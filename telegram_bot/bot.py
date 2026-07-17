from __future__ import annotations

import json
import logging
import os
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

from database.init import init_db
from database.session import get_session
from database.models import Vacancy
from parser import VacancyParser
from normalizer import Normalizer
from duplicate import DuplicateDetector
from poster import PosterGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)


def _load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')
    try:
        with open(config_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _format_salary(min_v: Optional[float], max_v: Optional[float]) -> str:
    if min_v is not None and max_v is not None:
        nf = lambda v: f'{v:,.0f}'
        return f'Rs. {nf(min_v)} — Rs. {nf(max_v)}/month'
    if min_v is not None:
        return f'Rs. {min_v:,.0f}+/month'
    if max_v is not None:
        return f'Up to Rs. {max_v:,.0f}/month'
    return 'Not specified'


def _format_field(label: str, value) -> str:
    return f'*{label}:* {value}' if value else ''


def _build_summary(vacancy: Vacancy) -> str:
    lines = [f'✅ *Vacancy #{vacancy.id} — Processed*']
    t = vacancy.title or 'Untitled'
    c = vacancy.company or 'Unknown'
    lines.append(f'')
    lines.append(_format_field('Job Title', t))
    lines.append(_format_field('Company', c))
    lines.append(_format_field('Location', vacancy.location))

    salary = _format_salary(vacancy.salary_min, vacancy.salary_max)
    lines.append(f'*Salary:* {salary}')

    if vacancy.job_type:
        lines.append(
            _format_field('Job Type', vacancy.job_type.replace('_', ' ').title())
        )
    if vacancy.experience_level:
        lines.append(
            _format_field('Experience', vacancy.experience_level.replace('_', ' ').title())
        )

    lines.append('')
    if vacancy.is_duplicate:
        lines.append(f'⚠️ Marked as duplicate of #{vacancy.duplicate_of}')
    else:
        lines.append('✅ No duplicate found')

    return '\n'.join(lines)


async def _process_vacancy(text: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    await update.message.reply_text('🔍 Parsing your vacancy message with Groq AI...')

    parser = VacancyParser(use_groq=True)
    normalizer = Normalizer()
    detector = DuplicateDetector()

    details = parser.parse(text)

    init_db()
    session = get_session()
    try:
        vacancy = Vacancy(
            title=details.title or 'Untitled',
            company=details.company or 'Unknown',
            description=details.description,
            raw_message=text,
            processed=False,
        )
        session.add(vacancy)
        session.commit()
        vacancy_id = vacancy.id
    except Exception as e:
        session.rollback()
        await update.message.reply_text(f'❌ Database error: {e}')
        return None
    finally:
        session.close()

    await update.message.reply_text(f'📝 Saving to database... (vacancy #{vacancy_id})')

    norm_result = normalizer.normalize(details, vacancy_id)
    if not norm_result.success:
        await update.message.reply_text(f'⚠️ Normalization warnings: {", ".join(norm_result.errors)}')

    dup_result = detector.detect(details, vacancy_id=vacancy_id)
    if dup_result.is_duplicate:
        await update.message.reply_text(
            f'⚠️ Duplicate detected! Matched vacancy #{dup_result.matched_vacancy_id} '
            f'(similarity: {dup_result.similarity_score:.2f})'
        )

    await update.message.reply_text('🎨 Generating poster...')
    poster = PosterGenerator()
    try:
        poster.generate(vacancy_id)
    except Exception as e:
        await update.message.reply_text(f'⚠️ Poster generation warning: {e}')

    session = get_session()
    try:
        v = session.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
        summary = _build_summary(v)

        keyboard = [[InlineKeyboardButton('📤 Publish to Facebook', callback_data=f'publish:{vacancy_id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(summary, parse_mode='Markdown', reply_markup=reply_markup)
    finally:
        session.close()

    return vacancy_id


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        '👋 *Ghost Vacancy Bot*\n\n'
        'Send me any job vacancy message and I will:\n'
        '1. Parse it with Groq AI\n'
        '2. Normalize & check for duplicates\n'
        '3. Generate a poster with AI image\n'
        '4. Let you publish to Facebook\n\n'
        'Just paste a vacancy message to get started!',
        parse_mode='Markdown',
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = update.message.text.strip()
    logger.info(f'Message from {user.id} ({user.full_name}): {text[:50]}...')

    if not text:
        await update.message.reply_text('Please send a non-empty message.')
        return

    vid = await _process_vacancy(text, update, context)
    if vid:
        logger.info(f'Vacancy #{vid} processed successfully')
    else:
        logger.warning('Vacancy processing failed')


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if not query.data or not query.data.startswith('publish:'):
        await query.edit_message_text(text='Unknown action.')
        return

    try:
        vacancy_id = int(query.data.split(':', 1)[1])
    except (ValueError, IndexError):
        await query.edit_message_text(text='Invalid vacancy ID.')
        return

    cfg = _load_config()
    fb_cfg = cfg.get('facebook', {})
    token = fb_cfg.get('access_token', '')
    groups = fb_cfg.get('group_ids', [])

    if not token or not groups:
        await query.edit_message_text(
            text='⚠️ Facebook publishing is not configured.\n'
                 'Set `facebook.access_token` and `facebook.group_ids` in config/settings.json',
            parse_mode='Markdown',
        )
        return

    await query.edit_message_text(text='📤 Publishing to Facebook groups...')

    try:
        from publisher import FacebookPublisher, PublisherPipeline

        fb = FacebookPublisher(access_token=token, group_ids=groups)
        pipeline = PublisherPipeline([fb])
        results = pipeline.publish(vacancy_id)

        lines = ['*Publish Results:*']
        for r in results:
            if r.success:
                lines.append(f'✅ {r.platform}: published (ID: {r.post_id})')
            else:
                lines.append(f'❌ {r.platform}: {r.error}')
        await query.message.reply_text('\n'.join(lines), parse_mode='Markdown')
    except Exception as e:
        await query.message.reply_text(f'❌ Publish error: {e}')


def _load_token() -> str:
    cfg = _load_config()
    return cfg.get('telegram_bot', {}).get('token', '')


def main(token: Optional[str] = None) -> None:
    bot_token = token or _load_token()
    if not bot_token:
        logger.error('Telegram bot token not configured. Set telegram_bot.token in config/settings.json')
        return

    logger.info('Starting Ghost Vacancy Bot...')
    app = Application.builder().token(bot_token).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback, pattern='^publish:'))

    logger.info('Bot is polling...')
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
