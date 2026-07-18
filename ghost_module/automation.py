from __future__ import annotations

from datetime import datetime, time as dtime
from typing import Any, Dict, List, Optional

from database.init import init_db as _init_db
from database.models import AutomationRule, QueueItem, Vacancy
from database.session import get_session


def get_rules(active_only: bool = True) -> List[AutomationRule]:
    _init_db()
    with get_session() as session:
        q = session.query(AutomationRule)
        if active_only:
            q = q.filter(AutomationRule.is_active == True)
        return q.order_by(AutomationRule.created_at.desc()).all()


def get_rule(rule_id: int) -> Optional[AutomationRule]:
    _init_db()
    with get_session() as session:
        return session.query(AutomationRule).filter(AutomationRule.id == rule_id).first()


def add_rule(
    name: str,
    trigger: str = 'immediate',
    schedule_time: Optional[str] = None,
    schedule_days: Optional[List[int]] = None,
    platforms: Optional[List[str]] = None,
    conditions: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    _init_db()
    trigger = trigger.lower().strip()
    if trigger not in AutomationRule.TRIGGERS:
        raise ValueError(f"Invalid trigger '{trigger}'. Supported: {AutomationRule.TRIGGERS}")

    with get_session() as session:
        rule = AutomationRule(
            name=name.strip(),
            trigger=trigger,
            is_active=True,
            schedule_time=schedule_time,
            schedule_days=schedule_days or [],
            platforms=platforms or [],
            conditions=conditions or {},
        )
        session.add(rule)
        session.commit()
        return rule.id


def update_rule(rule_id: int, **kwargs) -> bool:
    _init_db()
    allowed = {'name', 'is_active', 'trigger', 'schedule_time',
               'schedule_days', 'platforms', 'conditions'}
    with get_session() as session:
        rule = session.query(AutomationRule).filter(AutomationRule.id == rule_id).first()
        if not rule:
            return False
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                setattr(rule, k, v)
        session.commit()
        return True


def delete_rule(rule_id: int) -> bool:
    _init_db()
    with get_session() as session:
        rule = session.query(AutomationRule).filter(AutomationRule.id == rule_id).first()
        if not rule:
            return False
        session.delete(rule)
        session.commit()
        return True


def _matches_conditions(rule: AutomationRule, vacancy) -> bool:
    conds = rule.conditions or {}
    if not conds:
        return True

    if 'min_salary' in conds and conds['min_salary'] is not None:
        if (vacancy.salary_min or 0) < conds['min_salary']:
            return False
    if 'max_salary' in conds and conds['max_salary'] is not None:
        if (vacancy.salary_max or 0) > conds['max_salary']:
            return False
    if 'job_types' in conds and conds['job_types']:
        if (vacancy.job_type or '') not in conds['job_types']:
            return False
    if 'experience_levels' in conds and conds['experience_levels']:
        if (vacancy.experience_level or '') not in conds['experience_levels']:
            return False
    if 'min_confidence' in conds and conds['min_confidence'] is not None:
        from validator import validate_extraction
        from parser import JobDetails
        jd = JobDetails(
            title=vacancy.title, company=vacancy.company,
            location=vacancy.location, description=vacancy.description,
            salary_min=vacancy.salary_min, salary_max=vacancy.salary_max,
            job_type=vacancy.job_type, experience_level=vacancy.experience_level,
        )
        vr = validate_extraction(jd)
        if vr.overall_confidence < conds['min_confidence']:
            return False

    return True


def _is_schedule_due(rule: AutomationRule) -> bool:
    if rule.trigger != 'scheduled':
        return True
    if not rule.schedule_time:
        return True

    now = datetime.utcnow()
    try:
        hour, minute = (rule.schedule_time.split(':') if ':' in rule.schedule_time else (rule.schedule_time, '0'))
        sched = dtime(int(hour), int(minute))
        current = dtime(now.hour, now.minute)
        if current < sched:
            return False
    except (ValueError, IndexError):
        return True

    if rule.schedule_days:
        today = now.weekday()
        if today not in rule.schedule_days:
            return False

    return True


def _platforms_for_rule(rule: AutomationRule) -> Optional[List[str]]:
    p = rule.platforms
    return p if p else None


def match_rules_for_vacancy(vacancy_id: int) -> List[Dict[str, Any]]:
    _init_db()
    matches = []
    rules = get_rules(active_only=True)

    with get_session() as session:
        vacancy = session.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
        if not vacancy:
            return matches

        for rule in rules:
            if not _matches_conditions(rule, vacancy):
                continue
            if not _is_schedule_due(rule):
                continue

            matches.append({
                'rule_id': rule.id,
                'rule_name': rule.name,
                'trigger': rule.trigger,
                'platforms': _platforms_for_rule(rule),
            })

    return matches


def apply_rules_to_queue(queue_id: int) -> Dict[str, Any]:
    _init_db()
    with get_session() as session:
        qi = session.query(QueueItem).filter(QueueItem.id == queue_id).first()
        if not qi:
            return {'applied': False, 'error': 'Queue item not found'}

        if qi.status != 'queued':
            return {'applied': False, 'error': f"Status is '{qi.status}', not queued"}

        matches = match_rules_for_vacancy(qi.vacancy_id)
        if not matches:
            return {'applied': True, 'matches': [], 'publish': False}

        should_publish = any(
            m['trigger'] == 'immediate' or _is_schedule_due(get_rule(m['rule_id']))
            for m in matches
        )

        if should_publish:
            qi.scheduled_at = None
        else:
            for m in matches:
                if m['trigger'] == 'scheduled':
                    rule = get_rule(m['rule_id'])
                    if rule and rule.schedule_time:
                        now = datetime.utcnow()
                        try:
                            h, mn = rule.schedule_time.split(':')
                            sched = now.replace(hour=int(h), minute=int(mn), second=0, microsecond=0)
                            if sched < now:
                                sched = sched.replace(day=sched.day + 1)
                            qi.scheduled_at = sched
                        except (ValueError, IndexError):
                            pass
                    break

        session.commit()

    return {
        'applied': True,
        'matches': matches,
        'publish': should_publish,
        'scheduled_at': qi.scheduled_at.isoformat() if qi.scheduled_at else None,
    }


def process_pending_scheduled() -> List[int]:
    _init_db()
    now = datetime.utcnow()
    ready_ids = []
    with get_session() as session:
        items = session.query(QueueItem).filter(
            QueueItem.status == 'queued',
            QueueItem.scheduled_at.isnot(None),
            QueueItem.scheduled_at <= now,
        ).all()
        for item in items:
            item.scheduled_at = None
            ready_ids.append(item.id)
        session.commit()
    return ready_ids
