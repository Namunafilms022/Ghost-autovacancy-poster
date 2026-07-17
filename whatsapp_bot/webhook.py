from __future__ import annotations

import json
import logging
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, request, jsonify

from database.init import init_db
from database.session import get_session, SessionLocal
from database.models import Vacancy
from parser import VacancyParser
from normalizer import Normalizer
from duplicate import DuplicateDetector
from poster import PosterGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('whatsapp-webhook')

app = Flask(__name__)


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


def _build_result(vacancy: Vacancy) -> dict:
    salary = _format_salary(vacancy.salary_min, vacancy.salary_max)

    lines = [f'✅ *Vacancy #{vacancy.id}*']
    lines.append(f'*Title:* {vacancy.title or "Untitled"}')
    lines.append(f'*Company:* {vacancy.company or "Unknown"}')
    if vacancy.location:
        lines.append(f'*Location:* {vacancy.location}')
    lines.append(f'*Salary:* {salary}')
    if vacancy.job_type:
        lines.append(f'*Type:* {vacancy.job_type.replace("_", " ").title()}')
    if vacancy.experience_level:
        lines.append(f'*Experience:* {vacancy.experience_level.replace("_", " ").title()}')

    if vacancy.is_duplicate:
        lines.append(f'⚠️ Duplicate of #{vacancy.duplicate_of}')
    else:
        lines.append('✅ No duplicate')

    poster_image = None
    try:
        from poster.poster import _generate_pollinations_prompt, _build_pollinations_url
        prompt = _generate_pollinations_prompt(
            vacancy.title or 'Job Vacancy',
            vacancy.company or '',
            vacancy.job_type,
        )
        poster_image = _build_pollinations_url(prompt)
    except Exception:
        pass

    return {
        'success': True,
        'vacancy_id': vacancy.id,
        'summary': '\n'.join(lines),
        'poster_image': poster_image,
        'is_duplicate': vacancy.is_duplicate,
        'duplicate_of': vacancy.duplicate_of,
    }


@app.route('/webhook/process-vacancy', methods=['POST'])
def process_vacancy():
    data = request.get_json(silent=True)
    if not data or 'message' not in data:
        return jsonify({'success': False, 'error': 'Missing "message" field'}), 400

    raw = data['message'].strip()
    if not raw:
        return jsonify({'success': False, 'error': 'Empty message'}), 400

    group_name = data.get('group_name', 'unknown')
    sender = data.get('sender', 'unknown')
    logger.info(f'Processing vacancy from {sender} in {group_name}')

    try:
        init_db()
        parser = VacancyParser(use_groq=True)
        normalizer = Normalizer()
        detector = DuplicateDetector()
        poster_gen = PosterGenerator()

        details = parser.parse(raw)

        session = get_session()
        try:
            vacancy = Vacancy(
                title=details.title or 'Untitled',
                company=details.company or 'Unknown',
                description=details.description,
                raw_message=raw,
                processed=False,
            )
            session.add(vacancy)
            session.commit()
            vacancy_id = vacancy.id
        except Exception as e:
            session.rollback()
            session.close()
            return jsonify({'success': False, 'error': f'DB error: {e}'}), 500

        session.close()

        norm_result = normalizer.normalize(details, vacancy_id)
        if not norm_result.success:
            logger.warning(f'Normalization warnings for #{vacancy_id}: {norm_result.errors}')

        dup_result = detector.detect(details, vacancy_id=vacancy_id)

        try:
            poster_gen.generate(vacancy_id)
        except Exception as e:
            logger.warning(f'Poster generation error for #{vacancy_id}: {e}')

        session = get_session()
        try:
            v = session.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
            result = _build_result(v)
            result['duplicate_info'] = {
                'is_duplicate': dup_result.is_duplicate,
                'matched_id': dup_result.matched_vacancy_id,
                'similarity': dup_result.similarity_score,
            }

            if dup_result.is_duplicate:
                result['summary'] += f'\n⚠️ Duplicate of vacancy #{dup_result.matched_vacancy_id} (similarity: {dup_result.similarity_score:.2f})'

            return jsonify(result), 200
        finally:
            session.close()

    except Exception as e:
        logger.exception('Pipeline error')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/webhook/publish-facebook', methods=['POST'])
def publish_facebook():
    data = request.get_json(silent=True)
    if not data or 'vacancy_id' not in data:
        return jsonify({'success': False, 'error': 'Missing "vacancy_id"'}), 400

    vacancy_id = int(data['vacancy_id'])
    logger.info(f'Publishing vacancy #{vacancy_id} to Facebook')

    try:
        from publisher import FacebookPublisher, PublisherPipeline

        cfg = _load_config().get('facebook', {})
        token = cfg.get('access_token', '')
        groups = cfg.get('group_ids', [])

        if not token or not groups:
            return jsonify({
                'success': False,
                'error': 'Facebook not configured. Set access_token and group_ids in config.',
            }), 400

        fb = FacebookPublisher(access_token=token, group_ids=groups)
        pipeline = PublisherPipeline([fb])
        results = pipeline.publish(vacancy_id)

        response = {'success': True, 'results': []}
        for r in results:
            response['results'].append({
                'platform': r.platform,
                'success': r.success,
                'post_id': r.post_id,
                'url': r.url,
                'error': r.error,
            })

        return jsonify(response), 200

    except Exception as e:
        logger.exception('Facebook publish error')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/webhook/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'whatsapp-webhook'}), 200


def main():
    cfg = _load_config()
    port = cfg.get('whatsapp_bot', {}).get('webhook_port', 5001)
    logger.info(f'Starting webhook server on port {port}')
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    main()
