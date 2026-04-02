"""Backfill missing course summaries using Gemini."""

from django.core.management.base import BaseCommand
from django.db.models import Q

from amherst_coursework_algo.models import Course
from amherst_coursework_algo.management.commands.new_load_courses import (
    Command as NewLoadCoursesCommand,
)


class Command(BaseCommand):
    help = "Generate summaries for courses that do not have one yet"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Optional max number of courses to process",
        )

    def handle(self, *args, **options):
        limit = options.get("limit")
        missing_qs = Course.objects.filter(Q(summary__isnull=True) | Q(summary="")).order_by(
            "id"
        )

        total_missing = missing_qs.count()
        self.stdout.write(f"Courses missing summaries: {total_missing}")

        processed = 0
        generated = 0
        skipped = 0

        for course in missing_qs.iterator():
            if limit is not None and generated >= limit:
                break

            summary_text = NewLoadCoursesCommand.generate_course_summary(
                course.courseName,
                course.courseDescription or "",
            )
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
