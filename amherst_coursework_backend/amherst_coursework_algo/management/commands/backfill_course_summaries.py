"""Backfill missing course summaries using course_summaries.json."""

import json
import os
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.conf import settings

from amherst_coursework_algo.models import Course


class Command(BaseCommand):
    help = "Generate summaries for courses that do not have one yet using course_summaries.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Optional max number of courses to process",
        )
        parser.add_argument(
            "--file",
            type=str,
            default="amherst_coursework_algo/parse_course_catalogue/course_summaries.json",
            help="Path to the course summaries JSON file relative to backend root",
        )

    def handle(self, *args, **options):
        limit = options.get("limit")
        file_path = options.get("file")

        if not os.path.exists(file_path):
            self.stderr.write(f"File not found: {file_path}")
            return

        with open(file_path, "r") as f:
            summaries_data = json.load(f)

        missing_qs = (
            Course.objects.filter(Q(summary__isnull=True) | Q(summary=""))
            .prefetch_related("courseCodes")
            .order_by("id")
        )

        total_missing = missing_qs.count()
        self.stdout.write(f"Courses missing summaries: {total_missing}")

        processed = 0
        generated = 0
        skipped = 0

        for course in missing_qs.iterator(chunk_size=200):
            if limit is not None and generated >= limit:
                break

            # course.courseCodes is a ManyToManyField reaching CourseCode objects
            summary_text = None
            for code_obj in course.courseCodes.all():
                # CourseCode.value is formatted like "COSC-111"
                # summaries_data keys are formatted like "COSC 111" (space instead of hyphen)
                code_str = code_obj.value.replace("-", " ")
                if code_str in summaries_data:
                    summary_text = summaries_data[code_str]
                    break

            if summary_text:
                course.summary = summary_text
                course.save(update_fields=["summary"])
                generated += 1
            else:
                skipped += 1

            processed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Summary backfill complete. Processed={processed}, Generated={generated}, Skipped={skipped}"
            )
        )
