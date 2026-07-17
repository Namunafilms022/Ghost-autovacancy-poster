from __future__ import annotations

import sys
from datetime import datetime, date
from pathlib import Path

from flask import Flask, render_template, abort

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.init import init_db
from database.session import get_session
from database.models import Vacancy, VacancyPoster, PublishedPost

app = Flask(__name__)


def _today_start() -> datetime:
    return datetime.combine(date.today(), datetime.min.time())


def _today_end() -> datetime:
    return datetime.combine(date.today(), datetime.max.time())


def _status_info(vacancy: Vacancy) -> tuple[str, str]:
    if vacancy.is_duplicate:
        return 'Duplicate', 'danger'
    if vacancy.processed:
        return 'Processed', 'success'
    return 'Pending', 'warning'


@app.route('/')
def home():
    init_db()
    session = get_session()

    ts = _today_start()
    te = _today_end()

    today_vacancies = session.query(Vacancy).filter(
        Vacancy.created_at.between(ts, te)
    ).count()

    today_duplicates = session.query(Vacancy).filter(
        Vacancy.created_at.between(ts, te),
        Vacancy.is_duplicate == True,
    ).count()

    today_published = session.query(PublishedPost).filter(
        PublishedPost.created_at.between(ts, te),
        PublishedPost.status == 'published',
    ).count()

    today_failed = session.query(PublishedPost).filter(
        PublishedPost.created_at.between(ts, te),
        PublishedPost.status == 'failed',
    ).count()

    recent = session.query(Vacancy).order_by(
        Vacancy.created_at.desc()
    ).limit(5).all()

    session.close()

    return render_template(
        'home.html',
        total_vacancies=today_vacancies,
        duplicates=today_duplicates,
        published=today_published,
        failed=today_failed,
        recent=recent,
        status_info=_status_info,
    )


@app.route('/vacancies')
def vacancies():
    init_db()
    session = get_session()

    all_vacancies = session.query(Vacancy).order_by(
        Vacancy.created_at.desc()
    ).all()

    session.close()

    return render_template(
        'vacancies.html',
        vacancies=all_vacancies,
        status_info=_status_info,
    )


@app.route('/vacancies/<int:vacancy_id>')
def vacancy_detail(vacancy_id: int):
    init_db()
    session = get_session()

    vacancy = session.query(Vacancy).filter(
        Vacancy.id == vacancy_id
    ).first()

    if not vacancy:
        session.close()
        abort(404)

    poster = session.query(VacancyPoster).filter(
        VacancyPoster.vacancy_id == vacancy_id
    ).order_by(VacancyPoster.created_at.desc()).first()

    posts = session.query(PublishedPost).filter(
        PublishedPost.vacancy_id == vacancy_id
    ).order_by(PublishedPost.created_at.desc()).all()

    original = None
    if vacancy.duplicate_of:
        original = session.query(Vacancy).filter(
            Vacancy.id == vacancy.duplicate_of
        ).first()

    session.close()

    return render_template(
        'vacancy_detail.html',
        v=vacancy,
        poster=poster,
        posts=posts,
        original=original,
        status_info=_status_info,
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
