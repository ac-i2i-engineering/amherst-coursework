from django.core.management import call_command
from django.test import TestCase
from django.core.management.base import CommandError
from amherst_coursework_algo.models import (
    Course,
    Department,
    CourseCode,
    Professor,
    Section,
    Year,
    OverGuidelines,
    Prerequisites,
    PrerequisiteSet,
)
import os
import json


class LoadCoursesCommandTest(TestCase):
    def setUp(self):
        self.json_file_path = "/tmp/test_courses.json"
        self.course_data = [
            {
                "id": 5140111,
                "courseLink": "amherst.edu",
                "courseName": "Intro to Comp Sci I",
                "courseCodes": ["COSC111"],
                "deptNames": ["Computer Science"],
                "deptLinks": [
                    "https://www.amherst.edu/academiclife/departments/computer_science"
                ],
                "descriptionText": "This course introduces ideas and techniques that are fundamental to computer science.",
                "overGuidelines": {
                    "text": "Preference to first-year and sophomore students.",
                    "preferenceForMajors": False,
                    "overallCap": 40,
                    "freshmanCap": 40,
                    "sophomoreCap": 20,
                    "juniorCap": 20,
                    "seniorCap": 20,
                },
                "credits": 4,
                "prerequisites": {
                    "text": "none",
                    "required": [],
                    "recommended": [],
                    "profPermOver": False,
                },
                "corequisites": [5141111],
                "profNames": ["Lillian Pentecost", "Matteo Riondato"],
                "profLinks": [
                    "https://www.amherst.edu/people/facstaff/lpentecost",
                    "https://www.amherst.edu/people/facstaff/mriondato",
                ],
                "sections": {
                    "01": {
                        "daysOfWeek": "MWF",
                        "startTime": "09:00:00",
                        "endTime": "09:50:00",
                        "location": "SCCEA131",
                        "profName": "Lillian Pentecost",
                    },
                    "02": {
                        "daysOfWeek": "MWF",
                        "startTime": "13:00:00",
                        "endTime": "13:50:00",
                        "location": "SCCEA011",
                        "profName": "Matteo Riondato",
                    },
                },
                "offerings": {
                    "fall": [2019, 2022, 2023],
                    "fallLinks": [
                        "https://www.amherst.edu/academiclife/departments/courses/1920F/COSC/COSC-111-1920F",
                        "https://www.amherst.edu/academiclife/departments/courses/2223F/COSC/COSC-111-2223F",
                        "https://www.amherst.edu/academiclife/departments/courses/2324F/COSC/COSC-111-2324F",
                    ],
                    "spring": [2023, 2024],
                    "springLinks": [
                        "https://www.amherst.edu/academiclife/departments/courses/2223S/COSC/COSC-111-2223S",
                        "https://www.amherst.edu/academiclife/departments/courses/2324S/COSC/COSC-111-2324S",
                    ],
                    "january": [],
                    "januaryLinks": [],
                },
            }
        ]
        with open(self.json_file_path, "w") as f:
            json.dump(self.course_data, f)

    def tearDown(self):
        if os.path.exists(self.json_file_path):
            os.remove(self.json_file_path)

    def test_load_courses_success(self):
        call_command("load_courses", self.json_file_path)
        course = Course.objects.get(id=5140111)
        self.assertEqual(course.courseName, "Intro to Comp Sci I")
        self.assertEqual(
            course.courseDescription,
            "This course introduces ideas and techniques that are fundamental to computer science.",
        )
        self.assertEqual(course.credits, 4)
        self.assertEqual(course.courseLink, "amherst.edu")
        self.assertEqual(course.courseCodes.first().value, "COSC111")
        self.assertEqual(course.department.first().name, "Computer Science")
        self.assertEqual(course.professors.count(), 2)
        self.assertEqual(course.sections.count(), 2)
        self.assertEqual(course.fallOfferings.count(), 3)
        self.assertEqual(course.springOfferings.count(), 2)
        self.assertEqual(course.janOfferings.count(), 0)
        self.assertEqual(course.overGuidelines.overallCap, 40)

    def test_load_courses_invalid_id(self):
        self.course_data[0]["id"] = 99999999  # Invalid ID
        with open(self.json_file_path, "w") as f:
            json.dump(self.course_data, f)
        with self.assertRaises(ValueError):
            call_command("load_courses", self.json_file_path)
