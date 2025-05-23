"""
Load course data from JSON into database.

This Django management command reads course data from a JSON file and creates/updates
database records for courses and their related entities.



JSON Schema
-----------
The JSON file should follow this schema:

.. code-block:: javascript

    {
        "Department Name": [
            {
                "course_name": str,          // Full title of the course
                "description": str,          // Course description text
                "course_acronyms": [str],    // Course codes (e.g. ["COSC-111"])
                "departments": {             // Department names mapped to URLs
                    str: str                 // e.g. {"Computer Science": "https://..."}
                },

                // Optional fields
                "course_url": str,          // URL to course page
                "divisions": [str],         // Academic division names
                "keywords": [str],          // Course topic keywords
                "offerings": {              // Term offerings mapped to URLs
                    str: str                 // e.g. {"Spring 2024": "https://..."}
                },
                "section_information": {     // Section data keyed by section number
                    str: {                   // Contains professor, time, location info
                        "professor_name": str,
                        "professor_link": str,
                        "course_location": str,
                        "mon_start_time": str,
                        "mon_end_time": str,
                        // ... similar for tue/wed/thu/fri/sat/sun
                    }
                },
                "prerequisites": {           // Prerequisite course information
                    "text": str,            // Text description
                    "required": [[int]],     // Lists of required course IDs
                    "recommended": [int],    // List of recommended course IDs
                    "placement": int,        // Placement course ID
                    "professor_override": bool // Allow professor override
                },
                "corequisites": [int]       // IDs of corequisite courses
            }
        ]
    }

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
>>> python manage.py load_courses test.json

See Also
--------
amherst_coursework_algo.models : Database models used


Functions
---------
"""

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_time
from django.db import transaction
from amherst_coursework_algo.models import (
    Course,
    Department,
    CourseCode,
    PrerequisiteSet,
    Professor,
    Section,
    Year,
    Division,
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
            # Parse time like "9:00 AM" into Django time object
            parsed_time = datetime.strptime(time_str, "%I:%M %p")
            return parsed_time.time()
        except ValueError as e:
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
            * Processes prerequisites
            * Creates/updates professors
            * Processes offerings
            * Creates/updates course record
            * Creates/updates enrollment caps
            * Creates/updates sections
        """

        with open(options["json_file"]) as f:
            departments_courses_data = json.load(f)

        for department_list in departments_courses_data:
            courses_data = departments_courses_data[department_list]
            for course_data in courses_data:
                try:

                    divisions = []
                    for division in course_data.get("divisions", []):
                        division, _ = Division.objects.get_or_create(
                            name=division,
                        )
                        divisions.append(division)

                    keywords = []
                    for keyword in course_data.get("keywords", []):
                        keyword, _ = Keyword.objects.get_or_create(
                            name=keyword,
                        )
                        keywords.append(keyword)

                    codes = []
                    if len(course_data.get("course_acronyms", [])) == 0:
                        raise KeyError("No course codes found for course")

                    for code in course_data.get("course_acronyms", []):
                        code, _ = CourseCode.objects.get_or_create(
                            value=code,
                        )
                        codes.append(code)

                    departments = []
                    deptList = course_data.get("departments", {})
                    if len(deptList) == 0:
                        deptList = {"Other": INSTITUTIONAL_DOMAIN}
                        self.stdout.write(
                            self.style.WARNING(
                                f"Department not found for {course_data['course_name']}"
                            )
                        )
                        print(deptList)
                    i = 0
                    for department, link in deptList.items():
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
                        except:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"Failed to create course: {department} is not a valid department"
                                )
                            )
                            continue
                        departments.append(dept)
                        i += 1

                    recommended = [
                        Course.objects.get_or_create(id=rec)[0]
                        for rec in course_data.get("prerequisites", {}).get(
                            "recommended", []
                        )
                    ]

                    placement_id = course_data.get("prerequisites", {}).get("placement")
                    placementCourse = None
                    if placement_id:
                        placementCourse, _ = Course.objects.get_or_create(
                            id=placement_id
                        )

                    corequisites = [
                        Course.objects.get_or_create(id=rec)[0]
                        for rec in course_data.get("corequisites", {})
                    ]

                    fallOfferings = []
                    springOfferings = []
                    janOfferings = []

                    offerings = course_data.get("offerings", {})
                    for offering, link in offerings.items():
                        if offering == "Not offered":
                            continue
                        year, _ = Year.objects.get_or_create(
                            year=int(offering.split()[-1]),
                            link=link,
                        )
                        term = offering.split()[0]
                        if term == "Fall":
                            fallOfferings.append(year)
                        elif term == "Spring":
                            springOfferings.append(year)
                        elif term == "January":
                            janOfferings.append(year)
                        else:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"Failed to create course: {term} is not a valid term"
                                )
                            )
                            continue

                    id = 4000000
                    try:
                        id += (
                            DEPARTMENT_NAME_TO_NUMBER[departments[0].name] * 10000
                        )  # the second 2 digits are the department number
                    except KeyError:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Failed to create course: {departments[0].name} is not a valid department"
                            )
                        )
                        continue
                    if len(codes[0].value) == 9:
                        id += 1000  # 4th digit is half course flag (0 for full, 1 for half)
                    id += int(
                        codes[0].value[5:8]
                    )  # last 3 characters of course code are the course number

                    # Create course
                    course, _ = Course.objects.update_or_create(
                        id=id,
                        defaults={
                            "courseLink": course_data.get("course_url", ""),
                            "courseName": course_data["course_name"],
                            "credits": course_data.get("credits", 4),
                            "courseDescription": course_data["description"],
                            "placement_course": placementCourse,
                            "professor_override": course_data.get(
                                "prerequisites", {}
                            ).get("professor_override", False),
                            "prereqDescription": course_data.get(
                                "prerequisites", {}
                            ).get("text", ""),
                            "enrollmentText": course_data.get("overGuidelines", {}).get(
                                "text", ""
                            ),
                            "prefForMajor": course_data.get("overGuidelines", {}).get(
                                "preferenceForMajor", False
                            ),
                            "overallCap": course_data.get("overGuidelines", {}).get(
                                "overallCap", 0
                            ),
                            "freshmanCap": course_data.get("overGuidelines", {}).get(
                                "freshmanCap", 0
                            ),
                            "sophomoreCap": course_data.get("overGuidelines", {}).get(
                                "sophomoreCap", 0
                            ),
                            "juniorCap": course_data.get("overGuidelines", {}).get(
                                "juniorCap", 0
                            ),
                            "seniorCap": course_data.get("overGuidelines", {}).get(
                                "seniorCap", 0
                            ),
                        },
                    )

                    course.courseCodes.set(codes)
                    course.departments.set(departments)
                    course.corequisites.set(corequisites)
                    course.fallOfferings.set(fallOfferings)
                    course.springOfferings.set(springOfferings)
                    course.janOfferings.set(janOfferings)
                    course.divisions.set(divisions)
                    course.keywords.set(keywords)
                    course.recommended_courses.set(recommended)

                    for reqSet in course_data.get("prerequisites", {}).get(
                        "required", []
                    ):
                        prereq_set = PrerequisiteSet.objects.create(
                            prerequisite_for=course,
                        )
                        courses = [
                            Course.objects.get_or_create(id=req)[0] for req in reqSet
                        ]
                        prereq_set.courses.set(courses)

                    course.save()

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
                                section_data.get("professor_name", "Unknown Professor")
                                if section_data.get("professor_name")
                                else "Unknown Professor"
                            ),
                            link=(
                                section_data.get("professor_link", INSTITUTIONAL_DOMAIN)
                                if section_data.get("professor_link")
                                else INSTITUTIONAL_DOMAIN
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
                                "location": section_data.get(
                                    "course_location", "Unknown Location"
                                ),
                            },
                        )
                        sections.append(section)
                        professors.append(sectionProfessor)
                        i += 1

                    course.professors.set(professors)
                    course.courseMaterialsLink = courseMaterialsLink
                    course.save()

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
                            f"Failed to create course: {str(e)} for {course_data}"
                        )
                    )
                    raise
