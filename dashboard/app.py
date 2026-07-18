from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from flask import Blueprint, Flask, jsonify, render_template, request

from database.session import get_session
from database.models import Vacancy, VacancyPoster, PublishedPost
from duplicate import DuplicateDetector
from poster import PosterGenerator
from poster.company import get_company_branding

dashboard_bp = Blueprint('dashboard', __name__,
                         template_folder='templates',
                         static_folder='static')


def _load_validation() -> dict:
    path = Path('data/validation_results.json')
    if path.exists():
        try:
            results = json.loads(path.read_text())
            return {r.get('vacancy_id'): r for r in results}
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _get_status(v: Vacancy) -> dict:
    if v.is_duplicate:
        return {'label': 'Duplicate', 'class': 'status-dup', 'icon': '♻️'}
    if v.processed and not v.is_duplicate:
        return {'label': 'Processed', 'class': 'status-ok', 'icon': '✅'}
    return {'label': 'Raw', 'class': 'status-raw', 'icon': '📥'}


def _get_duplicate_info(v: Vacancy, session) -> dict:
    if v.is_duplicate and v.duplicate_of:
        orig = session.query(Vacancy).filter(Vacancy.id == v.duplicate_of).first()
        return {
            'is_duplicate': True,
            'matched_id': v.duplicate_of,
            'matched_title': orig.title if orig else 'N/A',
            'matched_company': orig.company if orig else 'N/A',
        }
    return {'is_duplicate': False}


def _get_poster_info(vacancy_id: int, session) -> Optional[dict]:
    poster = session.query(VacancyPoster).filter(
        VacancyPoster.vacancy_id == vacancy_id
    ).order_by(VacancyPoster.created_at.desc()).first()
    if poster:
        return {
            'id': poster.id,
            'html': poster.html_content,
            'theme': poster.theme,
            'created_at': poster.created_at.isoformat() if poster.created_at else None,
        }
    return None


def _get_publish_info(vacancy_id: int, session) -> list:
    posts = session.query(PublishedPost).filter(
        PublishedPost.vacancy_id == vacancy_id
    ).all()
    return [{
        'platform': p.platform,
        'status': p.status,
        'external_id': p.external_id,
        'url': p.url,
        'published_at': p.published_at.isoformat() if p.published_at else None,
    } for p in posts]


def _build_cards(session) -> list:
    validations = _load_validation()
    vacancies = session.query(Vacancy).order_by(Vacancy.created_at.desc()).all()
    cards = []
    for v in vacancies:
        status = _get_status(v)
        dup = _get_duplicate_info(v, session)
        poster = _get_poster_info(v.id, session)
        published = _get_publish_info(v.id, session)
        val = validations.get(v.id, {})

        has_poster = poster is not None
        published_count = sum(1 for p in published if p['status'] == 'published')
        pending_count = sum(1 for p in published if p['status'] == 'pending')
        failed_count = sum(1 for p in published if p['status'] == 'failed')

        cards.append({
            'id': v.id,
            'title': v.title or 'Untitled',
            'company': v.company or 'Unknown',
            'location': v.location,
            'salary_min': v.salary_min,
            'salary_max': v.salary_max,
            'job_type': v.job_type,
            'experience_level': v.experience_level,
            'created_at': v.created_at.isoformat() if v.created_at else None,
            'processed': v.processed,
            'status': status,
            'confidence': val.get('overall_confidence'),
            'confidence_level': val.get('overall_level'),
            'rejected': val.get('rejected', False),
            'rejection_reason': val.get('rejection_reason'),
            'extraction_fields': val.get('fields', {}),
            'duplicate': dup,
            'has_poster': has_poster,
            'poster': poster,
            'published': published,
            'published_count': published_count,
            'pending_count': pending_count,
            'failed_count': failed_count,
        })
    return cards


def _compute_stats(cards: list) -> dict:
    total = len(cards)
    processed = sum(1 for c in cards if c['processed'])
    raw = total - processed
    duplicates = sum(1 for c in cards if c['duplicate']['is_duplicate'])
    published = sum(1 for c in cards if c['published_count'] > 0)
    confs = [c['confidence'] for c in cards if c['confidence'] is not None]
    avg_conf = sum(confs) / len(confs) if confs else 0.0
    poster_count = sum(1 for c in cards if c['has_poster'])
    return {
        'total': total,
        'processed': processed,
        'raw': raw,
        'duplicates': duplicates,
        'published': published,
        'avg_conf': avg_conf,
        'posters': poster_count,
    }


@dashboard_bp.route('/')
def dashboard():
    session = get_session()
    try:
        cards = _build_cards(session)
        stats = _compute_stats(cards)
        return render_template('dashboard.html', cards=cards, stats=stats)
    finally:
        session.close()


@dashboard_bp.route('/api/vacancies')
def api_vacancies():
    session = get_session()
    try:
        return jsonify(_build_cards(session))
    finally:
        session.close()


@dashboard_bp.route('/api/vacancy/<int:vid>')
def api_vacancy(vid: int):
    session = get_session()
    try:
        cards = _build_cards(session)
        for c in cards:
            if c['id'] == vid:
                return jsonify(c)
        return jsonify({'error': 'Not found'}), 404
    finally:
        session.close()


@dashboard_bp.route('/api/vacancy/<int:vid>/regenerate', methods=['POST'])
def api_regenerate(vid: int):
    session = get_session()
    try:
        theme = (request.json or {}).get('theme')
        gen = PosterGenerator()
        html = gen.generate(vid, theme=theme)
        return jsonify({'success': True, 'poster_html': html})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@dashboard_bp.route('/api/vacancy/<int:vid>/duplicate-check', methods=['POST'])
def api_duplicate_check(vid: int):
    session = get_session()
    try:
        v = session.query(Vacancy).filter(Vacancy.id == vid).first()
        if not v:
            return jsonify({'error': 'Vacancy not found'}), 404

        from parser import JobDetails
        details = JobDetails(
            title=v.title, company=v.company, location=v.location,
            description=v.description, salary_min=v.salary_min,
            salary_max=v.salary_max,
        )
        detector = DuplicateDetector()
        result = detector.detect(details, vacancy_id=vid)
        return jsonify({
            'is_duplicate': result.is_duplicate,
            'similarity_score': result.similarity_score,
            'matched_vacancy_id': result.matched_vacancy_id,
            'reason': result.reason,
            'field_scores': result.field_scores,
            'merge_suggestion': result.merge_suggestion,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@dashboard_bp.route('/api/vacancy/<int:vid>/publish', methods=['POST'])
def api_publish(vid: int):
    from publisher import FacebookPublisher, PublisherPipeline
    session = get_session()
    try:
        v = session.query(Vacancy).filter(Vacancy.id == vid).first()
        if not v:
            return jsonify({'error': 'Vacancy not found'}), 404

        pipeline = PublisherPipeline()
        fb = FacebookPublisher()
        if fb.access_token and fb.group_ids:
            pipeline.add_publisher(fb)
        results = pipeline.publish(vid)
        return jsonify([{
            'platform': r.platform,
            'success': r.success,
            'post_id': r.post_id,
            'error': r.error,
        } for r in results])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@dashboard_bp.route('/api/vacancy/<int:vid>/delete', methods=['POST'])
def api_delete(vid: int):
    session = get_session()
    try:
        v = session.query(Vacancy).filter(Vacancy.id == vid).first()
        if not v:
            return jsonify({'error': 'Not found'}), 404

        session.query(VacancyPoster).filter(
            VacancyPoster.vacancy_id == vid).delete()
        session.query(PublishedPost).filter(
            PublishedPost.vacancy_id == vid).delete()
        session.delete(v)
        session.commit()
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@dashboard_bp.route('/api/vacancy/<int:vid>/edit', methods=['POST'])
def api_edit(vid: int):
    session = get_session()
    try:
        data = request.json or {}
        v = session.query(Vacancy).filter(Vacancy.id == vid).first()
        if not v:
            return jsonify({'error': 'Not found'}), 404

        for field in ('title', 'company', 'location', 'description',
                      'job_type', 'experience_level',
                      'salary_min', 'salary_max'):
            if field in data:
                setattr(v, field, data[field])
        v.updated_at = datetime.utcnow()
        session.commit()
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@dashboard_bp.route('/api/vacancy/<int:vid>/captions', methods=['POST'])
def api_captions(vid: int):
    session = get_session()
    try:
        v = session.query(Vacancy).filter(Vacancy.id == vid).first()
        if not v:
            return jsonify({'error': 'Not found'}), 404

        data = request.json or {}
        from captions import generate_captions
        result = generate_captions(
            title=data.get('title', v.title) or '',
            company=data.get('company', v.company) or '',
            location=data.get('location', v.location),
            salary_min=data.get('salary_min', v.salary_min),
            salary_max=data.get('salary_max', v.salary_max),
            job_type=data.get('job_type', v.job_type),
            experience_level=data.get('experience_level', v.experience_level),
            requirements=(data.get('requirements') or '').split('\n') if data.get('requirements') else None,
            benefits=(data.get('benefits') or '').split('\n') if data.get('benefits') else None,
            description=v.description,
        )
        out = {}
        for plat in ('facebook', 'instagram', 'linkedin', 'telegram', 'twitter'):
            cs = result.for_platform(plat)
            if cs:
                out[plat] = {
                    'caption': cs.caption,
                    'hashtags': cs.hashtags,
                    'call_to_action': cs.call_to_action,
                    'short_version': cs.short_version,
                    'long_version': cs.long_version,
                    'full_text': cs.full_text(),
                }
        return jsonify(out)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@dashboard_bp.route('/api/templates')
def api_templates():
    from poster.templates_marketplace import list_templates
    templates = list_templates()
    return jsonify([{
        'name': t.name,
        'label': t.label,
        'description': t.description,
        'theme': t.theme,
        'category': t.category,
        'font': t.font,
        'accent': t.accent,
        'bg': t.bg,
        'text_color': t.text_color,
        'surface': t.surface,
        'show_icons': t.show_icons,
        'icon_style': t.icon_style,
    } for t in templates])


@dashboard_bp.route('/social')
def social_page():
    from ghost_module.social_service import PLATFORM_ICONS, PLATFORM_COLORS
    return render_template('social.html',
        platforms=list(PLATFORM_ICONS.keys()),
        platform_icons=PLATFORM_ICONS,
        platform_colors=PLATFORM_COLORS,
    )


@dashboard_bp.route('/api/social/accounts')
def api_social_accounts():
    from ghost_module.social_service import get_accounts
    platform = request.args.get('platform', '')
    accounts = get_accounts(platform=platform or None, active_only=False)
    return jsonify([{
        'id': a.id,
        'platform': a.platform,
        'account_name': a.account_name,
        'account_id': a.account_id,
        'is_active': a.is_active,
        'has_token': bool(a.access_token),
        'token_expires_at': a.token_expires_at.isoformat() if a.token_expires_at else None,
        'created_at': a.created_at.isoformat() if a.created_at else None,
    } for a in accounts])


@dashboard_bp.route('/api/social/accounts', methods=['POST'])
def api_social_add():
    from ghost_module.social_service import add_account
    data = request.json or {}
    try:
        aid = add_account(
            platform=data.get('platform', ''),
            account_name=data.get('account_name', ''),
            account_id=data.get('account_id'),
            access_token=data.get('access_token'),
            extra_data=data.get('extra_data'),
        )
        return jsonify({'success': True, 'id': aid})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/social/accounts/<int:aid>', methods=['PUT'])
def api_social_update(aid: int):
    from ghost_module.social_service import update_account
    data = request.json or {}
    success = update_account(aid, **data)
    return jsonify({'success': success})


@dashboard_bp.route('/api/social/accounts/<int:aid>', methods=['DELETE'])
def api_social_delete(aid: int):
    from ghost_module.social_service import delete_account
    success = delete_account(aid)
    return jsonify({'success': success})


@dashboard_bp.route('/queue')
def queue_page():
    return render_template('queue.html')


@dashboard_bp.route('/api/queue')
def api_queue():
    from ghost_module.queue_service import get_queue, get_stats
    status = request.args.get('status', '')
    filters = {}
    if status:
        filters['status'] = status
    items = get_queue(filters)
    stats = get_stats()
    return jsonify({
        'items': [{
            'id': q.id,
            'vacancy_id': q.vacancy_id,
            'status': q.status,
            'platforms': q.platforms,
            'platform_states': q.platform_states,
            'poster_path': q.poster_path,
            'caption_path': q.caption_path,
            'retry_count': q.retry_count,
            'max_retries': q.max_retries,
            'error_message': q.error_message,
            'created_at': q.created_at.isoformat() if q.created_at else None,
            'updated_at': q.updated_at.isoformat() if q.updated_at else None,
            'published_at': q.published_at.isoformat() if q.published_at else None,
        } for q in items],
        'stats': {
            'total': stats.total,
            'queued': stats.queued,
            'publishing': stats.publishing,
            'published': stats.published,
            'failed': stats.failed,
            'partially_published': stats.partially_published,
            'draft': stats.draft,
            'retry_count': stats.retry_count,
            'avg_publish_time': stats.avg_publish_time,
        },
    })


@dashboard_bp.route('/api/queue/<int:qid>/retry', methods=['POST'])
def api_queue_retry(qid: int):
    from ghost_module.queue_service import retry_failed
    success = retry_failed(qid)
    return jsonify({'success': success})


@dashboard_bp.route('/api/queue/retry-all', methods=['POST'])
def api_queue_retry_all():
    from ghost_module.queue_service import retry_failed_all
    count = retry_failed_all()
    return jsonify({'success': True, 'count': count})


@dashboard_bp.route('/api/queue/<int:qid>', methods=['DELETE'])
def api_queue_delete(qid: int):
    from ghost_module.queue_service import delete_queue_item
    success = delete_queue_item(qid)
    return jsonify({'success': success})


@dashboard_bp.route('/api/queue/<int:qid>/publish', methods=['POST'])
def api_queue_publish(qid: int):
    from ghost_module.publish_manager import publish_queue_item
    result = publish_queue_item(qid)
    return jsonify(result)


@dashboard_bp.route('/api/queue/publish-pending', methods=['POST'])
def api_queue_publish_pending():
    from ghost_module.publish_manager import publish_pending
    result = publish_pending()
    return jsonify(result)


@dashboard_bp.route('/api/worker/status')
def api_worker_status():
    from ghost_module.worker import worker_status
    return jsonify(worker_status())


@dashboard_bp.route('/api/worker/start', methods=['POST'])
def api_worker_start():
    from ghost_module.worker import start_worker
    interval = (request.json or {}).get('poll_interval', 30)
    success = start_worker(poll_interval=interval)
    return jsonify({'success': success, **worker_status()})


@dashboard_bp.route('/api/worker/stop', methods=['POST'])
def api_worker_stop():
    from ghost_module.worker import stop_worker
    success = stop_worker()
    return jsonify({'success': success})


@dashboard_bp.route('/analytics')
def analytics_page():
    return render_template('analytics.html')


@dashboard_bp.route('/api/analytics/overview')
def api_analytics_overview():
    from ghost_module.analytics import get_overview, get_recent_activity, get_platform_failure_rate
    days = request.args.get('days', 30, type=int)
    return jsonify({
        'overview': get_overview(days=days),
        'recent': get_recent_activity(limit=20),
        'failure_rates': get_platform_failure_rate(days=days),
    })


@dashboard_bp.route('/automation')
def automation_page():
    return render_template('automation.html')


@dashboard_bp.route('/api/automation/rules')
def api_automation_rules():
    from ghost_module.automation import get_rules
    rules = get_rules(active_only=False)
    return jsonify([{
        'id': r.id,
        'name': r.name,
        'is_active': r.is_active,
        'trigger': r.trigger,
        'schedule_time': r.schedule_time,
        'schedule_days': r.schedule_days,
        'platforms': r.platforms,
        'conditions': r.conditions,
        'created_at': r.created_at.isoformat() if r.created_at else None,
    } for r in rules])


@dashboard_bp.route('/api/automation/rules', methods=['POST'])
def api_automation_add():
    from ghost_module.automation import add_rule
    data = request.json or {}
    try:
        rid = add_rule(
            name=data.get('name', ''),
            trigger=data.get('trigger', 'immediate'),
            schedule_time=data.get('schedule_time'),
            schedule_days=data.get('schedule_days'),
            platforms=data.get('platforms'),
            conditions=data.get('conditions'),
        )
        return jsonify({'success': True, 'id': rid})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@dashboard_bp.route('/api/automation/rules/<int:rid>', methods=['PUT'])
def api_automation_update(rid: int):
    from ghost_module.automation import update_rule
    data = request.json or {}
    success = update_rule(rid, **data)
    return jsonify({'success': success})


@dashboard_bp.route('/api/automation/rules/<int:rid>', methods=['DELETE'])
def api_automation_delete(rid: int):
    from ghost_module.automation import delete_rule
    success = delete_rule(rid)
    return jsonify({'success': success})


@dashboard_bp.route('/api/automation/apply/<int:qid>', methods=['POST'])
def api_automation_apply(qid: int):
    from ghost_module.automation import apply_rules_to_queue
    result = apply_rules_to_queue(qid)
    return jsonify(result)


@dashboard_bp.route('/editor/<int:vid>')
def editor(vid: int):
    session = get_session()
    try:
        v = session.query(Vacancy).filter(Vacancy.id == vid).first()
        if not v:
            return 'Vacancy not found', 404

        poster = _get_poster_info(vid, session)
        themes = [
            'minimal', 'glass', 'dark_neon', 'corporate_hiring_red',
            'ghost', 'cyberpunk', 'blue_professional',
        ]
        from poster.backgrounds import CATEGORIES
        from poster.themes import ALL_THEMES

        font_families = sorted(set(
            t.font.heading for t in ALL_THEMES
        ))

        requirements = ''
        benefits = ''
        if v.raw_message:
            from duplicate.detector import _get_req_benefits
            reqs, bens = _get_req_benefits(v.raw_message)
            requirements = '\n'.join(reqs)
            benefits = '\n'.join(bens)

        return render_template('editor.html',
            vacancy={
                'id': v.id,
                'title': v.title or '',
                'company': v.company or '',
                'location': v.location or '',
                'salary_min': v.salary_min,
                'salary_max': v.salary_max,
                'job_type': v.job_type or '',
                'experience_level': v.experience_level or '',
                'requirements': requirements,
                'benefits': benefits,
                'theme': poster['theme'] if poster else 'dark_neon',
                'poster_html': poster['html'] if poster else '',
            },
            themes=themes,
            categories=CATEGORIES,
            font_families=font_families,
        )
    finally:
        session.close()


@dashboard_bp.route('/api/vacancy/<int:vid>/editor-render', methods=['POST'])
def api_editor_render(vid: int):
    session = get_session()
    try:
        v = session.query(Vacancy).filter(Vacancy.id == vid).first()
        if not v:
            return jsonify({'error': 'Not found'}), 404

        data = request.json or {}

        from poster.poster import _build_theme_context, _build_layer_context_for_theme
        from poster.themes import get_theme
        from poster.backgrounds import detect_category, background_svg, overlay_gradient
        from poster.layers import build_layer_context
        from jinja2 import Environment, FileSystemLoader
        import os as _os

        theme_name = data.get('theme') or 'dark_neon'
        category = data.get('category') or detect_category(
            data.get('title', v.title), '')

        theme = get_theme(theme_name)
        ctx = _build_theme_context(theme)
        ctx.update(_build_layer_context_for_theme(theme_name, theme, category))

        company_name = data.get('company', v.company) or 'Unknown Company'
        from poster.company import get_company_branding
        branding = get_company_branding(company_name)
        ctx.update({
            'company_logo': branding.logo_data_uri,
            'company_logo_is_placeholder': branding.logo_is_placeholder,
            'company_website': branding.website_url,
            'brand_color': branding.brand_color,
            'brand_accent': branding.accent_color,
        })

        req_lines = (data.get('requirements') or '').strip().split('\n')
        req_lines = [r.strip() for r in req_lines if r.strip()]
        ben_lines = (data.get('benefits') or '').strip().split('\n')
        ben_lines = [b.strip() for b in ben_lines if b.strip()]

        ctx.update({
            'vacancy_id': v.id,
            'title': data.get('title', v.title) or 'Untitled Position',
            'company': company_name,
            'location': data.get('location', v.location),
            'job_type': data.get('job_type', v.job_type) or '',
            'experience_level': data.get('experience_level', v.experience_level) or '',
            'salary_min': data.get('salary_min', v.salary_min),
            'salary_max': data.get('salary_max', v.salary_max),
            'requirements': req_lines,
            'benefits': ben_lines,
            'contact_email': None,
            'contact_phone': None,
            'created_at': v.created_at.strftime('%B %d, %Y') if v.created_at else 'N/A',
        })

        templ_dir = _os.path.join(_os.path.dirname(__file__), '..', 'poster', 'templates')
        env = Environment(loader=FileSystemLoader(templ_dir))
        template = env.get_template('theme.html')
        html = template.render(**ctx)

        return jsonify({'success': True, 'poster_html': html, 'theme': theme_name})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


def create_app():
    from database.init import init_db
    init_db()
    app = Flask(__name__)
    app.register_blueprint(dashboard_bp, url_prefix='')

    from validator.dashboard import dashboard_bp as validator_bp
    app.register_blueprint(validator_bp)

    return app


def run_dashboard(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    app = create_app()
    app.run(host=host, port=port, debug=debug)
