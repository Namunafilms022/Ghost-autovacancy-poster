#!/usr/bin/env python3
"""
Ghost-autovacancy-poster — Full pipeline CLI.

Usage:
    python main.py --input vacancies/
    python main.py --input message.txt
    python main.py --api [-p 8000]
    python main.py --dashboard [-p 5000]
    python main.py --worker [--poll-interval 30]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import List, Optional

from database.init import init_db
from database.session import get_session
from database.models import Vacancy

from reader import FileReader, ReaderPipeline
from parser import VacancyParser
from normalizer import Normalizer
from text_cleaner import TextCleaner
from validator import validate_extraction
from validator.dashboard import save_validation_result
from duplicate import DuplicateDetector
from poster import PosterGenerator
from poster.themes import AVAILABLE_THEMES, auto_select_theme
from publisher import FacebookPublisher, PublisherPipeline


def _load_vacancies(input_path: Path) -> List[str]:
    if input_path.is_file():
        return [input_path.read_text(encoding='utf-8')]
    reader = FileReader(input_path)
    return reader.read_all()


def _parse_message(parser: VacancyParser, raw: str, idx: int) -> Optional[dict]:
    try:
        details = parser.parse(raw)
        return {
            'title': details.title,
            'company': details.company,
            'details': details,
        }
    except Exception as e:
        print(f"  [SKIP] Parse failed for message #{idx}: {e}")
        return None


def _save_to_db(pipeline: ReaderPipeline, raw: str, idx: int) -> Optional[int]:
    try:
        result = pipeline.ingest_message(raw, source=f'main:{idx}')
        if result.success:
            print(f"  [DB]   Saved as vacancy #{result.vacancy_id}")
            return result.vacancy_id
        print(f"  [FAIL] DB save failed: {result.error}")
        return None
    except Exception as e:
        print(f"  [FAIL] DB save error: {e}")
        return None


def _normalize(normalizer: Normalizer, details, vacancy_id: int) -> bool:
    try:
        result = normalizer.normalize(details, vacancy_id)
        if result.success:
            print(f"  [OK]   Normalized vacancy #{vacancy_id}")
            return True
        for err in result.errors:
            print(f"  [WARN] {err}")
        return False
    except Exception as e:
        print(f"  [FAIL] Normalize error: {e}")
        return False


def _validate(details, threshold: float) -> bool:
    try:
        result = validate_extraction(details, threshold)
        overall = result.overall_confidence
        level = result.overall_level.value
        print(f"  [VAL]  Confidence: {overall:.0%} ({level})")

        for name, fv in result.fields.items():
            if not fv.passed:
                print(f"  [VAL]  {name}: {fv.confidence:.0%} — {', '.join(fv.issues)}")

        if result.rejected:
            print(f"  [REJ]  {result.rejection_reason}")

        result.vacancy_id = id(details)
        save_validation_result(result)
        return not result.rejected
    except Exception as e:
        print(f"  [FAIL] Validation error: {e}")
        return True


def _check_duplicate(detector: DuplicateDetector, details, vacancy_id: int) -> None:
    try:
        result = detector.detect(details, vacancy_id=vacancy_id)
        if result.is_duplicate:
            print(f"  [DUP]  Duplicate of #{result.matched_vacancy_id} "
                  f"(score={result.similarity_score:.2f})")
        else:
            print(f"  [OK]   No duplicate found (best={result.similarity_score:.2f})")
    except Exception as e:
        print(f"  [FAIL] Duplicate check error: {e}")


def _generate_poster(poster: PosterGenerator, vacancy_id: int,
                     theme: Optional[str] = None) -> Optional[str]:
    try:
        html = poster.generate(vacancy_id, theme=theme)
        print(f"  [OK]   Poster generated for #{vacancy_id}"
              f"{' (auto-theme)' if theme is None else ' (' + theme + ')'}")
        return html
    except Exception as e:
        print(f"  [FAIL] Poster generation error: {e}")
        return None


def _publish(pipeline: PublisherPipeline, vacancy_id: int) -> None:
    try:
        results = pipeline.publish(vacancy_id)
        for r in results:
            status = '✅' if r.success else '❌'
            print(f"  [{status}] {r.platform}: "
                  f"{'published (id=' + r.post_id + ')' if r.success else r.error}")
    except Exception as e:
        print(f"  [FAIL] Publish error: {e}")


def run_pipeline(input_path: Path, theme: Optional[str] = None,
                 no_publish: bool = False, dry_run: bool = False,
                 threshold: float = 0.7, auto_theme: bool = False) -> int:
    init_db()
    print(f"\n{'='*60}")
    print(f"  Ghost-autovacancy-poster")
    print(f"  Input: {input_path}")
    if dry_run:
        print(f"  Mode:  DRY RUN (no DB changes)")
    if no_publish:
        print(f"  Mode:  Skip publishing")
    print(f"{'='*60}\n")

    messages = _load_vacancies(input_path)
    if not messages:
        print("No vacancy messages found.")
        return 1

    print(f"Found {len(messages)} message(s).\n")

    text_cleaner = TextCleaner()
    parser = VacancyParser()
    reader_pipeline = ReaderPipeline()
    normalizer = Normalizer()
    detector = DuplicateDetector()

    poster_theme = None if auto_theme else (theme or 'dark_neon')
    poster = PosterGenerator()
    publisher_pipeline = PublisherPipeline()

    if not no_publish:
        fb = FacebookPublisher()
        if fb.access_token and fb.group_ids:
            publisher_pipeline.add_publisher(fb)

    processed = 0
    skipped = 0

    for idx, raw in enumerate(messages, 1):
        print(f"[{idx}/{len(messages)}] Processing...")

        raw = text_cleaner.clean(raw) or raw
        print(f"  [CLEAN] Text cleaned")

        parsed = _parse_message(parser, raw, idx)
        if not parsed:
            skipped += 1
            continue

        if parsed['title']:
            print(f"  Title:   {parsed['title']}")
        if parsed['company']:
            print(f"  Company: {parsed['company']}")

        if dry_run:
            print(f"  [DRY]   Would save to DB, normalize, check dupes, "
                  f"generate poster{' & publish' if not no_publish else ''}")
            processed += 1
            continue

        if not _validate(parsed['details'], threshold):
            print(f"  [SKIP] Rejected by validation")
            skipped += 1
            continue

        vacancy_id = _save_to_db(reader_pipeline, raw, idx)
        if vacancy_id is None:
            skipped += 1
            continue

        _normalize(normalizer, parsed['details'], vacancy_id)
        _check_duplicate(detector, parsed['details'], vacancy_id)
        _generate_poster(poster, vacancy_id, theme=poster_theme)

        if not no_publish:
            _publish(publisher_pipeline, vacancy_id)

        processed += 1
        print()

    print(f"{'='*60}")
    print(f"  Done. {processed} processed, {skipped} skipped.")
    print(f"{'='*60}\n")
    return 0 if skipped == 0 else 1


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Ghost-autovacancy-poster — Full pipeline CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--pipeline', '-P',
        action='store_true',
        help='Run the production Ghost pipeline (uses ghost_module API)',
    )
    parser.add_argument(
        '--worker', '-w',
        action='store_true',
        help='Start the background publish worker',
    )
    parser.add_argument(
        '--poll-interval', type=int, default=30,
        help='Worker poll interval in seconds (default: 30)',
    )
    parser.add_argument(
        '--dashboard', '-d',
        action='store_true',
        help='Start the web dashboard (overrides --input)',
    )
    parser.add_argument(
        '--api', '-a',
        action='store_true',
        help='Start the FastAPI webhook server (port 8000)',
    )
    parser.add_argument(
        '--api-port', type=int, default=8000,
        help='API server port (default: 8000)',
    )
    parser.add_argument(
        '--host', type=str, default='0.0.0.0',
        help='Dashboard host (default: 0.0.0.0)',
    )
    parser.add_argument(
        '--port', '-p', type=int, default=5000,
        help='Dashboard port (default: 5000)',
    )
    parser.add_argument(
        '--input', '-i',
        type=str,
        default=None,
        help='Path to a .txt file or directory containing vacancy messages',
    )
    parser.add_argument(
        '--theme', '-t',
        type=str,
        default=None,
        choices=AVAILABLE_THEMES + [None],
        help=f'Poster theme. Available: {", ".join(AVAILABLE_THEMES)} (default: dark_neon)',
    )
    parser.add_argument(
        '--auto-theme',
        action='store_true',
        help='Auto-select theme based on vacancy type (overrides --theme)',
    )
    parser.add_argument(
        '--no-publish',
        action='store_true',
        help='Skip publishing to social media',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Parse and show results without saving to DB',
    )
    parser.add_argument(
        '--threshold', '-c',
        type=float,
        default=0.7,
        help='Minimum extraction confidence threshold (default: 0.7)',
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only run validation, skip DB/poster/publish',
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if args.worker:
        from database.init import init_db
        init_db()
        from ghost_module.worker import run_worker_forever
        run_worker_forever(poll_interval=args.poll_interval)
        return 0

    if args.api:
        from api_server import run_api
        run_api(host=args.host, port=args.api_port)
        return 0

    if args.dashboard:
        from database.init import init_db
        init_db()
        from dashboard import run_dashboard
        print(f"Starting dashboard at http://{args.host}:{args.port}")
        run_dashboard(host=args.host, port=args.port, debug=False)
        return 0

    if not args.input:
        print("Error: provide --input or use --dashboard for web UI.")
        return 1

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: '{args.input}' not found.")
        return 1

    if args.pipeline:
        from database.init import init_db
        init_db()
        from ghost_module.pipeline import run_pipeline as ghost_pipeline
        result = ghost_pipeline(
            input_path=str(input_path),
            threshold=args.threshold,
        )
        return 0 if result.failed == 0 else 1

    return run_pipeline(
        input_path=input_path,
        theme=args.theme,
        no_publish=args.no_publish,
        dry_run=args.dry_run or args.validate_only,
        threshold=args.threshold,
        auto_theme=args.auto_theme,
    )


if __name__ == '__main__':
    sys.exit(main())
