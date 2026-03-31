"""
Load course data from JSON into database.

This Django management command reads course data from a JSON file and creates/updates
database records for courses and their related entities.

Notes
-----
- Uses atomic transactions for database consistency
- Course ID format: 4DDTCCC where:
    - 4: Amherst College identifier
    - DD: Department number (00-99)
    - T: Credit type (0=full, 1=half)
    - CCC: Course number
- Logs success/failure messages

Examples
--------
>>> python manage.py load_courses course_parsed.json

See Also
--------
amherst_coursework_algo.models : Database models used
"""

from django.core.management.base import BaseCommand
from django.db import transaction
import os
from amherst_coursework_algo.models import (
    Course,
    Department,
    CourseCode,
    Professor,
    Section,
    Keyword,
)
from amherst_coursework_algo.config.course_dictionaries import (
    DEPARTMENT_NAME_TO_NUMBER,
    DEPARTMENT_NAME_TO_CODE,
    MISMATCHED_DEPARTMENT_NAMES,
)
import json
from datetime import datetime
from django.conf import settings


INSTITUTIONAL_DOMAIN = settings.INSTITUTIONAL_DOMAIN


class Command(BaseCommand):

    def parse_ampm_time(time_str):
        """
        Parse a time string in AM/PM format into a Django time object.

        Parameters
        ----------
        time_str : str
            A string representing time in 'HH:MM AM/PM' format (e.g. '9:00 AM')

        Returns
        -------
        time or None
            A Django time object if parsing is successful, None otherwise

        Examples
        --------
        >>> parse_ampm_time('9:00 AM')
        datetime.time(9, 0)
        >>> parse_ampm_time('invalid')
        None
        >>> parse_ampm_time(None)
        None
        """
        if not time_str or time_str == "null":
            return None
        try:
            parsed_time = datetime.strptime(time_str, "%I:%M %p")
            return parsed_time.time()
        except ValueError:
            print(f"Error parsing time: {time_str}")
            return None

    help = "Load courses from JSON file"

    def add_arguments(self, parser):
        parser.add_argument("json_file", type=str, help="Path to JSON file")

    @transaction.atomic
    def handle(self, *args, **options):
        """Process JSON course data and load into database.

        Parameters
        ----------
        args : tuple
            Variable length argument list
        options : dict
            Must contain 'json_file' key with path to JSON data

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If course ID is invalid (not 1000000-9999999)
        Exception
            If error occurs during database operations

        Operation Flow
        --------------
        1. Reads JSON file
        2. For each course:
            * Creates course ID
            * Creates/updates departments
            * Creates/updates course codes
            * Creates/updates keywords (from course_tags)
            * Creates/updates professors
            * Creates/updates course record
            * Creates/updates sections
        """

        with open(options["json_file"]) as f:
            courses_data = json.load(f)

        for course_key, course_data in courses_data.items():
            try:

                # -------------------------------
                # Keywords (from course_tags)
                # -------------------------------
                keywords = []
                for tag in course_data.get("course_tags", []):
                    keyword, _ = Keyword.objects.get_or_create(name=tag)
                    keywords.append(keyword)

                # -------------------------------
                # Course codes
                # -------------------------------
                codes = []
                if len(course_data.get("course_acronyms", [])) == 0:
                    raise KeyError(f"No course codes found for course {course_key}")

                for code in course_data.get("course_acronyms", []):
                    code, _ = CourseCode.objects.get_or_create(value=code)
                    codes.append(code)

                # -------------------------------
                # Departments
                # -------------------------------
                departments = []
                dept_list = course_data.get("departments", {})
                if len(dept_list) == 0:
                    dept_list = {"Other": INSTITUTIONAL_DOMAIN}
                    self.stdout.write(
                        self.style.WARNING(
                            f"Department not found for {course_key}"
                        )
                    )

                for department, link in dept_list.items():
                    try:
                        if department not in DEPARTMENT_NAME_TO_CODE:
                            department = MISMATCHED_DEPARTMENT_NAMES[department]
                        dept, _ = Department.objects.get_or_create(
                            name=department,
                            defaults={
                                "code": DEPARTMENT_NAME_TO_CODE[department],
                                "link": link,
                            },
                        )
                    except Exception:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Failed to create course: {department} is not a valid department"
                            )
                        )
                        continue
                    departments.append(dept)

                if not departments:
                    raise ValueError(f"No valid departments found for {course_key}")

                # -------------------------------
                # Course ID
                # -------------------------------
                id = 4000000
                try:
                    id += DEPARTMENT_NAME_TO_NUMBER[departments[0].name] * 10000
                except KeyError:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Failed to create course: {departments[0].name} is not a valid department"
                        )
                    )
                    continue

                if len(codes[0].value) == 9:
                    id += 1000  # 4th digit is half course flag (0 for full, 1 for half)
                id += int(codes[0].value[5:8])  # last 3 digits of course code

                # -------------------------------
                # Create/update course
                # -------------------------------
                course, _ = Course.objects.update_or_create(
                    id=id,
                    defaults={
                        "courseName": course_data["course_title"],
                        "courseDescription": (
                            course_data.get("course_description")
                            or course_data.get("description")
                            or ""
                        ),
                    },
                )

                course.courseCodes.set(codes)
                course.departments.set(departments)
                course.keywords.set(keywords)

                course.save()

                # -------------------------------
                # Sections
                # -------------------------------
                professors = []
                sections = []
                i = 0
                courseMaterialsLink = INSTITUTIONAL_DOMAIN

                for section_number, section_data in course_data.get(
                    "section_information", {}
                ).items():
                    if i == 0:
                        courseMaterialsLink = section_data.get(
                            "course_materials_links", INSTITUTIONAL_DOMAIN
                        )

                    sectionProfessor, _ = Professor.objects.get_or_create(
                        name=(
                            section_data.get("professor_name")
                            or "Unknown Professor"
                        ),
                        link=(
                            section_data.get("professor_link")
                            or INSTITUTIONAL_DOMAIN
                        ),
                    )

                    section, _ = Section.objects.update_or_create(
                        section_number=section_number,
                        section_for=course,
                        defaults={
                            "monday_start_time": Command.parse_ampm_time(
                                section_data.get("mon_start_time")
                            ),
                            "monday_end_time": Command.parse_ampm_time(
                                section_data.get("mon_end_time")
                            ),
                            "tuesday_start_time": Command.parse_ampm_time(
                                section_data.get("tue_start_time")
                            ),
                            "tuesday_end_time": Command.parse_ampm_time(
                                section_data.get("tue_end_time")
                            ),
                            "wednesday_start_time": Command.parse_ampm_time(
                                section_data.get("wed_start_time")
                            ),
                            "wednesday_end_time": Command.parse_ampm_time(
                                section_data.get("wed_end_time")
                            ),
                            "thursday_start_time": Command.parse_ampm_time(
                                section_data.get("thu_start_time")
                            ),
                            "thursday_end_time": Command.parse_ampm_time(
                                section_data.get("thu_end_time")
                            ),
                            "friday_start_time": Command.parse_ampm_time(
                                section_data.get("fri_start_time")
                            ),
                            "friday_end_time": Command.parse_ampm_time(
                                section_data.get("fri_end_time")
                            ),
                            "saturday_start_time": Command.parse_ampm_time(
                                section_data.get("sat_start_time")
                            ),
                            "saturday_end_time": Command.parse_ampm_time(
                                section_data.get("sat_end_time")
                            ),
                            "sunday_start_time": Command.parse_ampm_time(
                                section_data.get("sun_start_time")
                            ),
                            "sunday_end_time": Command.parse_ampm_time(
                                section_data.get("sun_end_time")
                            ),
                            "professor": sectionProfessor,
                            "location": section_data.get("course_location") or "Unknown Location",
                        },
                    )
                    sections.append(section)
                    professors.append(sectionProfessor)
                    i += 1

                course.professors.set(professors)
                course.courseMaterialsLink = courseMaterialsLink
                course.save()

                # -------------------------------
                # Dummy section fallback
                # -------------------------------
                if course.sections.all().count() == 0:
                    dummy_professor, _ = Professor.objects.get_or_create(
                        name="TBA", link=INSTITUTIONAL_DOMAIN
                    )
                    dummy_section, _ = Section.objects.update_or_create(
                        section_number="01",
                        section_for=course,
                        defaults={"professor": dummy_professor, "location": "TBA"},
                    )
                    course.professors.add(dummy_professor)
                    course.save()
                    self.stdout.write(
                        self.style.WARNING(
                            f'Added dummy section for course "{course.courseName}"'
                        )
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created course "{course.courseName}"'
                    )
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to create course: {str(e)} for {course_key}"
                    )
                )
                raise