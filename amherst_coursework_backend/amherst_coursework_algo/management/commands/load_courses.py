# amherst_coursework_algo/management/commands/load_courses.py
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_time
from django.db import transaction
from amherst_coursework_algo.models import (
    Course,
    Department,
    CourseCode,
    OverGuidelines,
    Prerequisites,
    PrerequisiteSet,
    Professor,
    Section,
    Year,
)
import json


class Command(BaseCommand):
    help = "Load courses from JSON file"

    def add_arguments(self, parser):
        parser.add_argument("json_file", type=str, help="Path to JSON file")

    @transaction.atomic
    def handle(self, *args, **options):

        with open(options["json_file"]) as f:
            courses_data = json.load(f)

        for course_data in courses_data:
            try:
                if not (1000000 <= course_data.get("id", 0) <= 9999999):
                    raise ValueError(f"Invalid course ID: {course_data.get('id')}")

                # Create or get departments
                departments = []
                deptList = course_data.get("deptNames", [])
                deptLinks = course_data.get("deptLinks", [])
                for i in range(len(deptList)):
                    dept, _ = Department.objects.get_or_create(
                        name=deptList[i],
                        defaults={
                            "code": deptList[i][
                                :4
                            ].upper(),  # Assume code is first 4 characters of name; will have to convert to some sort of lookup table later
                            "link": deptLinks[i],
                        },
                    )
                    departments.append(dept)

                codes = []
                for code in course_data.get("courseCodes", []):
                    code, _ = CourseCode.objects.get_or_create(
                        value=code,
                    )
                    codes.append(code)

                recommended = [
                    Course.objects.get_or_create(id=rec)[0]
                    for rec in course_data.get("prerequisites", {}).get(
                        "recommended", []
                    )
                ]

                required = []
                for reqSet in course_data.get("prerequisites", {}).get("required", []):
                    prereq_set = PrerequisiteSet.objects.create()
                    courses = [
                        Course.objects.get_or_create(id=req)[0] for req in reqSet
                    ]
                    prereq_set.courses.set(courses)
                    required.append(prereq_set)

                placement_id = course_data.get("prerequisites", {}).get("placement")
                placementCourse = None
                if placement_id:
                    placementCourse, _ = Course.objects.get_or_create(id=placement_id)

                prereq, _ = Prerequisites.objects.get_or_create(
                    description=course_data.get("prerequisites", {}).get("text", ""),
                    professor_override=course_data.get("prerequisites", {}).get(
                        "profPermOver", False
                    ),
                    placement_course=placementCourse,
                )

                prereq.recommended_courses.set(recommended)
                prereq.required_courses.set(required)

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
                fallOfferingsData = course_data.get("offerings", {}).get("fall", [])
                fallLinks = course_data.get("offerings", {}).get("fallLinks", [])
                for i in range(len(fallOfferingsData)):
                    year, _ = Year.objects.get_or_create(
                        year=fallOfferingsData[i],
                        link=fallLinks[i],
                    )
                    fallOfferings.append(year)

                springOfferings = []
                springOfferingsData = course_data.get("offerings", {}).get("spring", [])
                springLinks = course_data.get("offerings", {}).get("springLinks", [])
                for i in range(len(springOfferingsData)):
                    year, _ = Year.objects.get_or_create(
                        year=springOfferingsData[i],
                        link=springLinks[i],
                    )
                    springOfferings.append(year)

                janOfferings = []
                janOfferingsData = course_data.get("offerings", {}).get("jan", [])
                janLinks = course_data.get("offerings", {}).get("janLinks", [])
                for i in range(len(janOfferingsData)):
                    year, _ = Year.objects.get_or_create(
                        year=janOfferingsData[i],
                        link=janLinks[i],
                    )
                    janOfferings.append(year)

                # Create course
                course, _ = Course.objects.update_or_create(
                    id=course_data["id"],
                    defaults={
                        "courseLink": course_data.get("courseLink", ""),
                        "courseName": course_data["courseName"],
                        "credits": course_data.get("credits", 4),
                        "courseDescription": course_data["descriptionText"],
                        "prerequisites": prereq,
                    },
                )

                course.courseCodes.set(codes)
                course.department.set(departments)
                course.corequisites.set(corequisites)
                course.professors.set(professors)
                course.fallOfferings.set(fallOfferings)
                course.springOfferings.set(springOfferings)
                course.janOfferings.set(janOfferings)

                overGuide, _ = OverGuidelines.objects.update_or_create(
                    myCourse=course,
                    defaults={
                        "text": course_data.get("overGuidelines", {}).get("text", ""),
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

                course.overGuidelines = overGuide
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
                        myCourse=course,
                        defaults={
                            "days": section_data["daysOfWeek"],
                            "start_time": parse_time(section_data["startTime"]),
                            "end_time": parse_time(section_data["endTime"]),
                            "location": section_data["location"],
                            "professor": sectionProfessor,
                        },
                    )
                    sections.append(section)

                course.sections.set(sections)

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created course "{course.courseName}"'
                    )
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to create course: {str(e)}")
                )
