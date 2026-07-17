#!/usr/bin/env python3
"""
Ghost-autovacancy-poster — Full pipeline CLI.

Usage:
    python main.py --input vacancies/
    python main.py --input message.txt
    python main.py --input vacancies/ --no-publish
    python main.py --input vacancies/ --dry-run
    python main.py --input vacancies/ --theme dark
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
from duplicate import DuplicateDetector
from poster import PosterGenerator
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


def _generate_poster(poster: PosterGenerator, vacancy_id: int) -> Optional[str]:
    try:
        html = poster.generate(vacancy_id)
        print(f"  [OK]   Poster generated for #{vacancy_id}")
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


def run_pipeline(input_path: Path, theme: str = 'default',
                 no_publish: bool = False, dry_run: bool = False) -> int:
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

    parser = VacancyParser()
    reader_pipeline = ReaderPipeline()
    normalizer = Normalizer()
    detector = DuplicateDetector()

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

        vacancy_id = _save_to_db(reader_pipeline, raw, idx)
        if vacancy_id is None:
            skipped += 1
            continue

        _normalize(normalizer, parsed['details'], vacancy_id)
        _check_duplicate(detector, parsed['details'], vacancy_id)
        _generate_poster(poster, vacancy_id)

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
        '--input', '-i',
        type=str,
        required=True,
        help='Path to a .txt file or directory containing vacancy messages',
    )
    parser.add_argument(
        '--theme', '-t',
        type=str,
        default='default',
        choices=['default', 'dark', 'minimal'],
        help='Poster theme (default: default)',
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
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: '{args.input}' not found.")
        return 1

    return run_pipeline(
        input_path=input_path,
        theme=args.theme,
        no_publish=args.no_publish,
        dry_run=args.dry_run,
    )


if __name__ == '__main__':
    sys.exit(main())
