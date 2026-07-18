from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from flask import Blueprint, Flask, jsonify, render_template_string, request

from database.session import get_session
from database.models import Vacancy

dashboard_bp = Blueprint('validator_dashboard', __name__,
                         template_folder='templates',
                         url_prefix='/validator')

_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Extraction Confidence Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; padding: 24px; }
  .container { max-width: 1200px; margin: 0 auto; }
  h1 { font-size: 1.75rem; margin-bottom: 24px; color: #f1f5f9; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .stat-card { background: #1e293b; border-radius: 10px; padding: 20px; border: 1px solid #334155; }
  .stat-card h3 { font-size: 0.85rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }
  .stat-card .value { font-size: 2rem; font-weight: 700; margin-top: 8px; }
  .stat-card .value.green { color: #22c55e; }
  .stat-card .value.yellow { color: #eab308; }
  .stat-card .value.red { color: #ef4444; }
  .card { background: #1e293b; border-radius: 10px; padding: 20px; margin-bottom: 16px; border: 1px solid #334155; }
  .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
  .card-header h2 { font-size: 1.1rem; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 0.8rem; font-weight: 600; }
  .badge.excellent { background: #166534; color: #22c55e; }
  .badge.good { background: #713f12; color: #eab308; }
  .badge.fair { background: #7c2d12; color: #f97316; }
  .badge.poor { background: #7f1d1d; color: #ef4444; }
  .badge.missing { background: #1e293b; color: #64748b; border: 1px solid #475569; }
  .badge.rejected { background: #7f1d1d; color: #fca5a5; }
  .field-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 8px; }
  .field-item { padding: 8px 12px; background: #0f172a; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; }
  .field-item .label { color: #94a3b8; font-size: 0.85rem; }
  .field-item .score { font-weight: 600; font-size: 0.9rem; }
  .field-item .score.high { color: #22c55e; }
  .field-item .score.mid { color: #eab308; }
  .field-item .score.low { color: #ef4444; }
  .progress-bar { width: 100%; height: 8px; background: #334155; border-radius: 999px; margin-top: 8px; overflow: hidden; }
  .progress-fill { height: 100%; border-radius: 999px; transition: width 0.3s; }
  .progress-fill.green { background: #22c55e; }
  .progress-fill.yellow { background: #eab308; }
  .progress-fill.red { background: #ef4444; }
  .empty { text-align: center; padding: 40px; color: #64748b; }
  .rejection { margin-top: 8px; padding: 8px 12px; background: #7f1d1d; border-radius: 6px; color: #fca5a5; font-size: 0.85rem; border: 1px solid #991b1b; }
  .vacancy-link { color: #60a5fa; text-decoration: none; }
  .vacancy-link:hover { text-decoration: underline; }
</style>
</head>
<body>
<div class="container">
<h1>Extraction Confidence Dashboard</h1>
<div class="stats">
  <div class="stat-card">
    <h3>Total Vacancies</h3>
    <div class="value">{{ stats.total }}</div>
  </div>
  <div class="stat-card">
    <h3>Accepted</h3>
    <div class="value green">{{ stats.accepted }}</div>
  </div>
  <div class="stat-card">
    <h3>Rejected</h3>
    <div class="value red">{{ stats.rejected }}</div>
  </div>
  <div class="stat-card">
    <h3>Avg Confidence</h3>
    <div class="value {{ 'green' if stats.avg_conf >= 0.7 else 'yellow' if stats.avg_conf >= 0.5 else 'red' }}">{{ '%.0f'|format(stats.avg_conf * 100) }}%</div>
  </div>
</div>
{% if not results %}
<div class="card"><div class="empty">No validation results yet. Run the pipeline first.</div></div>
{% endif %}
{% for r in results %}
<div class="card" id="v-{{ r.vacancy_id }}">
  <div class="card-header">
    <div>
      <h2>Vacancy #{{ r.vacancy_id }}</h2>
      {% if r.rejected %}
      <span class="badge rejected">REJECTED</span>
      {% endif %}
    </div>
    <div>
      <span class="badge {{ r.overall_level }}">{{ r.overall_level|upper }}</span>
      <span style="margin-left:8px;font-weight:700;">{{ '%.0f'|format(r.overall_confidence * 100) }}%</span>
    </div>
  </div>
  <div class="progress-bar">
    <div class="progress-fill {{ 'green' if r.overall_confidence >= 0.7 else 'yellow' if r.overall_confidence >= 0.5 else 'red' }}" style="width:{{ r.overall_confidence * 100 }}%"></div>
  </div>
  {% if r.rejection_reason %}
  <div class="rejection">{{ r.rejection_reason }}</div>
  {% endif %}
  <div class="field-grid" style="margin-top:12px;">
    {% for name, fv in r.fields.items() %}
    <div class="field-item">
      <span class="label">{{ name }}</span>
      <span class="score {{ 'high' if fv.confidence >= 0.7 else 'mid' if fv.confidence >= 0.5 else 'low' }}">
        {{ '%.0f'|format(fv.confidence * 100) }}%
      </span>
    </div>
    {% endfor %}
  </div>
</div>
{% endfor %}
</div>
</body>
</html>'''


@dashboard_bp.route('/')
def dashboard():
    results_path = Path('data/validation_results.json')
    results = []
    stats = {'total': 0, 'accepted': 0, 'rejected': 0, 'avg_conf': 0.0}

    if results_path.exists():
        with open(results_path) as f:
            raw = json.load(f)
        results = raw
        stats['total'] = len(results)
        stats['rejected'] = sum(1 for r in results if r.get('rejected'))
        stats['accepted'] = stats['total'] - stats['rejected']
        if stats['total'] > 0:
            stats['avg_conf'] = sum(r.get('overall_confidence', 0) for r in results) / stats['total']

    return render_template_string(_HTML, results=results, stats=stats)


@dashboard_bp.route('/api/validation/<int:vacancy_id>')
def api_validation(vacancy_id: int):
    results_path = Path('data/validation_results.json')
    if results_path.exists():
        with open(results_path) as f:
            results = json.load(f)
        for r in results:
            if r.get('vacancy_id') == vacancy_id:
                return jsonify(r)
    return jsonify({'error': 'Not found'}), 404


@dashboard_bp.route('/api/validation')
def api_all_validations():
    results_path = Path('data/validation_results.json')
    if results_path.exists():
        with open(results_path) as f:
            return jsonify(json.load(f))
    return jsonify([])


def create_app():
    app = Flask(__name__)
    app.register_blueprint(dashboard_bp)
    return app


def run_dashboard(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    app = create_app()
    app.run(host=host, port=port, debug=debug)


def save_validation_result(result) -> None:
    path = Path('data/validation_results.json')
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = []
    if path.exists():
        with open(path) as f:
            existing = json.load(f)

    existing = [r for r in existing if r.get('vacancy_id') != result.vacancy_id]
    existing.append(result.to_dict())

    with open(path, 'w') as f:
        json.dump(existing, f, indent=2)
