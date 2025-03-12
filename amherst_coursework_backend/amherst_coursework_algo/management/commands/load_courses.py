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

"""A Django management command to load course data from a JSON file into the database.

This command reads course data from a specified JSON file and creates/updates corresponding
database records for courses and their related entities (departments, professors, sections, etc.).

Usage:
    python manage.py load_courses <path_to_json_file>

Args:
    json_file (str): Path to the JSON file containing course data. The JSON should contain an array
                     of course objects with fields matching the Course model structure.

Example:
    python manage.py load_courses courses.json

JSON Format Requirements:
    - Each course object must have:
        - course_name (str): Name of the course 
        - description (str): Course description
    - Optional fields include:
        - course_url (str): URL to course page
        - course_materials_links (list): List of course materials URLs
        - course_acronyms (list): List of course codes 
        - departments (dict): Department names mapped to dept URLs
        - prerequisites (dict): Course prerequisites information
            - text (str): Text description of prerequisites
            - required (list): List of required course ID sets
            - recommended (list): List of recommended course IDs
            - placement (int): ID of placement test course
            - professor_override (bool): Whether prof can override prereqs
        - corequisites (list): List of corequisite course IDs
        - profNames (list): List of professor names
        - profLinks (list): List of professor links
        - credits (int): Number of credits (default 4)
        - divisions (list): Academic divisions
        - keywords (list): Course keywords/tags
        - offerings (dict): Course offerings with links by term
        - sections (dict): Section information
        - overGuidelines (dict): Enrollment guidelines
            - text (str): Enrollment text
            - preferenceForMajor (bool): Preference for majors
            - overallCap (int): Overall enrollment cap
            - freshmanCap (int): Freshman cap
            - sophomoreCap (int): Sophomore cap
            - juniorCap (int): Junior cap
            - seniorCap (int): Senior cap

Notes:
    - Uses Django's atomic transaction to ensure database consistency
    - Will create new records or update existing ones based on primary keys 
    - Course IDs are automatically generated based on department and course number
    - Logs success/failure messages for each course processed
"""


class Command(BaseCommand):
    def parse_ampm_time(time_str):
        """
        Parse a time string in AM/PM format into a Django time object.

        Args:
            time_str (str): A string representing time in 'HH:MM AM/PM' format (e.g. '9:00 AM')

        Returns:
            time: A Django time object if parsing is successful, None otherwise

        Examples:
            >>> parse_ampm_time('9:00 AM')
            datetime.time(9, 0)
            >>> parse_ampm_time('invalid')
            None
            >>> parse_ampm_time(None)
            None
        """
        """Parse time string with AM/PM format"""
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

    """
        Process and load course data from a JSON file into the database.
        This method handles the creation and updating of course-related records in the database,
        including departments, course codes, prerequisites, professors, and course offerings.
        Args:
            *args: Variable length argument list.
            **options: Arbitrary keyword arguments. Must contain 'json_file' key with path to JSON data.
        Returns:
            None
        Raises:
            ValueError: If course ID is invalid (not between 1000000 and 9999999).
            Exception: If any error occurs during course creation/update process.
        The method performs the following operations:
        1. Reads course data from JSON file
        2. For each course:
            - Creates course ID
            - Creates/updates department records
            - Creates/updates course codes
            - Processes prerequisites (recommended, required, and placement courses)
            - Creates/updates professor records
            - Processes course offerings (fall, spring, and January terms)
            - Creates/updates the main course record
            - Creates/updates over-enrollment guidelines
            - Creates/updates course sections
        Success/failure messages are written to stdout using Django's management command styling.
        """

    @transaction.atomic
    def handle(self, *args, **options):

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
                        deptList = {"Other": "https://www.amherst.edu/"}
                        print(f"Department not found for {course_data['course_name']}")
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
                    courseMaterialsLink = "https://www.amherst.edu/"
                    for section_number, section_data in course_data.get(
                        "section_information", {}
                    ).items():
                        if i == 0:
                            courseMaterialsLink = section_data.get(
                                "course_materials_links", "https://www.amherst.edu/"
                            )
                        sectionProfessor, _ = Professor.objects.get_or_create(
                            name=(
                                section_data.get("professor_name", "Unknown Professor")
                                if section_data.get("professor_name")
                                else "Unknown Professor"
                            ),
                            link=(
                                section_data.get(
                                    "professor_link", "https://www.amherst.edu/"
                                )
                                if section_data.get("professor_link")
                                else "https://www.amherst.edu/"
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
