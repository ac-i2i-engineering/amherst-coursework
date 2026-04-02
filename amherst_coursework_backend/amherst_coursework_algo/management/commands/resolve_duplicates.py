from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from amherst_coursework_algo.models import Course


class Command(BaseCommand):
    help = (
        "Find duplicate courses by exact courseName and optionally merge duplicates into "
        "a primary course by combining course codes and departments."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show duplicate groups and merge actions without writing changes.",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Automatically confirm all proposed merges.",
        )
        parser.add_argument(
            "--name",
            type=str,
            default=None,
            help="Only process duplicates for one exact courseName.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        auto_yes = options.get("yes", False)
        target_name = options.get("name")

        duplicate_groups = (
            Course.objects.values("courseName")
            .exclude(courseName="")
            .annotate(course_count=Count("id"))
            .filter(course_count__gt=1)
            .order_by("courseName")
        )

        if target_name is not None:
            duplicate_groups = duplicate_groups.filter(courseName=target_name)

        groups_found = 0
        merges_completed = 0
        merges_skipped = 0
        merge_errors = 0

        for group in duplicate_groups:
            course_name = group["courseName"]
            courses = list(
                Course.objects.filter(courseName=course_name)
                .prefetch_related("courseCodes", "departments")
                .order_by("id")
            )

            if len(courses) < 2:
                continue

            groups_found += 1
            primary = courses[0]

            self.stdout.write(
                self.style.WARNING(
                    f"Duplicate group: {course_name} ({len(courses)} courses found)"
                )
            )
            self.stdout.write(
                f"Primary course (kept): id={primary.id}, "
                f"codes={self._codes_display(primary)}, "
                f"departments={self._departments_display(primary)}"
            )

            for duplicate in courses[1:]:
                self.stdout.write(
                    f"Candidate duplicate: id={duplicate.id}, "
                    f"codes={self._codes_display(duplicate)}, "
                    f"departments={self._departments_display(duplicate)}"
                )

                if not self._should_merge(
                    auto_yes=auto_yes,
                    course_name=course_name,
                    primary_id=primary.id,
                    duplicate_id=duplicate.id,
                ):
                    merges_skipped += 1
                    self.stdout.write(self.style.WARNING("Skipped by user."))
                    continue

                if dry_run:
                    merges_completed += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            "Dry-run: would merge duplicate into primary and delete duplicate."
                        )
                    )
                    continue

                try:
                    self._merge_courses(primary_id=primary.id, duplicate_id=duplicate.id)
                    merges_completed += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Merged duplicate id={duplicate.id} into primary id={primary.id}."
                        )
                    )
                except Exception as exc:
                    merge_errors += 1
                    self.stderr.write(
                        self.style.ERROR(
                            f"Failed merge for primary={primary.id}, duplicate={duplicate.id}: {exc}"
                        )
                    )

        if groups_found == 0:
            self.stdout.write(self.style.SUCCESS("No duplicate course names found."))

        self.stdout.write(
            self.style.SUCCESS(
                "Duplicate resolution complete. "
                f"groups_found={groups_found}, "
                f"merges_completed={merges_completed}, "
                f"merges_skipped={merges_skipped}, "
                f"merge_errors={merge_errors}, "
                f"dry_run={dry_run}"
            )
        )

    def _should_merge(self, auto_yes, course_name, primary_id, duplicate_id):
        if auto_yes:
            return True

        prompt = (
            f"Merge duplicate for '{course_name}'? "
            f"primary={primary_id}, duplicate={duplicate_id} [y/N]: "
        )
        response = input(prompt).strip().lower()
        return response in {"y", "yes"}

    @transaction.atomic
    def _merge_courses(self, primary_id, duplicate_id):
        primary = Course.objects.select_for_update().get(id=primary_id)
        duplicate = Course.objects.select_for_update().get(id=duplicate_id)

        primary.courseCodes.add(*duplicate.courseCodes.all())
        primary.departments.add(*duplicate.departments.all())

        duplicate.delete()

    def _codes_display(self, course):
        codes = [code.value for code in course.courseCodes.all()]
        if not codes:
            return "[]"
        return "[" + ", ".join(sorted(codes)) + "]"

    def _departments_display(self, course):
        departments = [dept.name for dept in course.departments.all()]
        if not departments:
            return "[]"
        return "[" + ", ".join(sorted(departments)) + "]"
