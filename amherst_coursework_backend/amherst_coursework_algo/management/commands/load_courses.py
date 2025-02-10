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
from amherst_coursework_algo.config.course_dictionaries import DEPARTMENT_NAME_TO_NUMBER
import json

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
        - id (int): Between 0000000 and 9999999 
        - courseName (str): Name of the course
        - descriptionText (str): Course description
    - Optional fields include:
        - deptNames (list): List of department names
        - deptLinks (list): List of department links
        - courseCodes (list): List of course codes
        - prerequisites (dict): Course prerequisites information
        - corequisites (list): List of corequisite course IDs
        - profNames (list): List of professor names
        - profLinks (list): List of professor links
        - offerings (dict): Course offerings by term
        - sections (dict): Section information
        - overGuidelines (dict): Enrollment guidelines

Example JSON:
[
    {
    "id": 5140111,
    "courseLink" : "amherst.edu",
    "courseName": "Intro to Comp Sci I",
    "courseCodes": ["COSC111"],
    "categories": ["programming", "computer science", "java"],
    "deptNames": ["Computer Science"],
    "deptLinks": [
        "https://www.amherst.edu/academiclife/departments/computer_science"
    ],
    "descriptionText": "This course introduces ideas and techniques that are fundamental to computer science. The course emphasizes procedural abstraction, algorithmic methods, and structured design techniques. Students will gain a working knowledge of a block-structured programming language and will use the language to solve a variety of problems illustrating ideas in computer science. A selection of other elementary topics will be presented. A laboratory section will meet once a week to give students practice with programming constructs.",
    "overGuidelines": {
        "text": "Preference to first-year and sophomore students.",
        "preferenceForMajors": false,
        "overallCap": 40,
        "freshmanCap": 40,
        "sophomoreCap": 20,
        "juniorCap": 20,
        "seniorCap": 20
    },
    "credits": 4,
    "prerequisites": {
        "text": "none",
        "required": [],
        "recommended": [],
        "profPermOver": false
    },
    "corequisites": [5141111],
    "profNames": ["Lillian Pentecost", "Matteo Riondato"],
    "profLinks": [
        "https://www.amherst.edu/people/facstaff/lpentecost",
        "https://www.amherst.edu/people/facstaff/mriondato"
    ],
    "sections": {
        "01": {
        "daysOfWeek": "MWF",
        "startTime": "09:00:00",
        "endTime": "09:50:00",
        "location": "SCCEA131",
        "profName": "Lillian Pentecost"
        },
        "02": {
        "daysOfWeek": "MWF",
        "startTime": "13:00:00",
        "endTime": "13:50:00",
        "location": "SCCEA011",
        "profName": "Matteo Riondato"
        }
    },
    "offerings": {
        "fall": [2019, 2022, 2023],
        "fallLinks": [
        "https://www.amherst.edu/academiclife/departments/courses/1920F/COSC/COSC-111-1920F",
        "https://www.amherst.edu/academiclife/departments/courses/2223F/COSC/COSC-111-2223F",
        "https://www.amherst.edu/academiclife/departments/courses/2324F/COSC/COSC-111-2324F"
        ],
        "spring": [2023, 2024],
        "springLinks": [
        "https://www.amherst.edu/academiclife/departments/courses/2223S/COSC/COSC-111-2223S",
        "https://www.amherst.edu/academiclife/departments/courses/2324S/COSC/COSC-111-2324S"
        ],
        "january": [],
        "januaryLinks": []
    }
    }
]

Notes:
    - Uses Django's atomic transaction to ensure database consistency
    - Will create new records or update existing ones based on primary keys
    - Logs success/failure messages for each course processed
"""


class Command(BaseCommand):
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
            - Validates course ID
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
            courses_data = json.load(f)

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
                    raise KeyError("No departments found for course")
                i = 0
                for department, link in deptList.items():
                    dept, _ = Department.objects.get_or_create(
                        name=department,
                        defaults={
                            "code": codes[i].value.split("-")[
                                0
                            ],  # Get department code from course code (assumes departments and course codes are listed in same order)
                        },
                    )
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
                    placementCourse, _ = Course.objects.get_or_create(id=placement_id)

                corequisites = [
                    Course.objects.get_or_create(id=rec)[0]
                    for rec in course_data.get("corequisites", {})
                ]

                professors = []
                profNames = course_data.get("profNames", [])
                profLinks = course_data.get("profLinks", [])
                for i in range(len(profNames)):
                    professor, _ = Professor.objects.update_or_create(
                        name=profNames[i], defaults={"link": profLinks[i]}
                    )
                    professors.append(professor)

                fallOfferings = []
                springOfferings = []
                janOfferings = []

                offerings = course_data.get("offerings", {})
                for offering, link in offerings.items():
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
                        "courseMaterialsLink": course_data.get(
                            "course_materials_links", [None]
                        )[0]
                        or "",
                        "placement_course": placementCourse,
                        "professor_override": course_data.get("prerequisites", {}).get(
                            "professor_override", False
                        ),
                        "prereqDescription": course_data.get("prerequisites", {}).get(
                            "text", ""
                        ),
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
                course.professors.set(professors)
                course.fallOfferings.set(fallOfferings)
                course.springOfferings.set(springOfferings)
                course.janOfferings.set(janOfferings)
                course.divisions.set(divisions)
                course.keywords.set(keywords)
                course.recommended_courses.set(recommended)

                for reqSet in course_data.get("prerequisites", {}).get("required", []):
                    prereq_set = PrerequisiteSet.objects.create(
                        prerequisite_for=course,
                    )
                    courses = [
                        Course.objects.get_or_create(id=req)[0] for req in reqSet
                    ]
                    prereq_set.courses.set(courses)

                course.save()

                sections = []
                for section_number, section_data in course_data.get(
                    "sections", {}
                ).items():
                    sectionProfessor, _ = Professor.objects.get_or_create(
                        name=section_data.get("profName", "")
                    )
                    section, _ = Section.objects.update_or_create(
                        section_number=section_number,
                        section_for=course,
                        defaults={
                            "days": section_data["daysOfWeek"],
                            "start_time": parse_time(section_data["startTime"]),
                            "end_time": parse_time(section_data["endTime"]),
                            "location": section_data["location"],
                            "professor": sectionProfessor,
                        },
                    )
                    sections.append(section)

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
