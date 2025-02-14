import pytest
from django.core.management import call_command
from django.test import TestCase
from amherst_coursework_algo.models import (
    Course,
    CourseCode,
    Department,
    Professor,
    Section,
    Year,
)
import json
from io import StringIO
from django.core.management.base import CommandError


class TestLoadCourses(TestCase):

    def test_load_basic_course_data(self):
        """Test loading basic course data without relationships"""

        test_data = [
            {
                "course_url": "https://test.edu/course1",
                "course_name": "Test Course 1",
                "course_acronyms": ["TEST-101"],
                "divisions": ["Humanities"],
                "departments": {"Computer Science": "https://test.edu/dept1"},
                "description": "Test course description",
            }
        ]

        with open("test_courses.json", "w") as f:
            json.dump(test_data, f)

        call_command("load_courses", "test_courses.json")

        # Verify course was created
        course = Course.objects.first()
        print(course.courseDescription)
        self.assertEqual(course.courseName, "Test Course 1")
        self.assertEqual(course.courseDescription, "Test course description")

    def test_load_course_with_offerings(self):
        """Test loading course with offerings data"""

        test_data = [
            {
                "course_name": "Test Course",
                "course_acronyms": ["TEST-101"],
                "departments": {"Computer Science": "https://test.edu/dept"},
                "offerings": {
                    "Fall 2023": "https://test.edu/fall2023",
                    "Spring 2024": "https://test.edu/spring2024",
                },
                "description": "Test course description",
            }
        ]

        with open("test_courses.json", "w") as f:
            json.dump(test_data, f)

        call_command("load_courses", "test_courses.json")

        # Verify offerings were created
        course = Course.objects.first()
        self.assertEqual(course.fallOfferings.count(), 1)
        self.assertEqual(course.springOfferings.count(), 1)

    def test_load_course_with_professors(self):
        """Test loading course with professor data"""

        test_data = [
            {
                "course_name": "Test Course",
                "course_acronyms": ["TEST-101"],
                "departments": {"Computer Science": "https://test.edu/dept"},
                "profNames": ["Dr. Test Professor"],
                "profLinks": ["https://test.edu/prof1"],
                "description": "Test course description",
            }
        ]

        with open("test_courses.json", "w") as f:
            json.dump(test_data, f)

        call_command("load_courses", "test_courses.json")

        # Verify professor was created and linked
        course = Course.objects.first()
        self.assertEqual(course.professors.count(), 1)
        professor = course.professors.first()
        self.assertEqual(professor.name, "Dr. Test Professor")
        self.assertEqual(professor.link, "https://test.edu/prof1")

    def test_invalid_json(self):
        """Test handling of invalid JSON file"""
        with open("nonexistent.json", "w") as f:
            f.write("invalid json")

        with self.assertRaises(json.JSONDecodeError):
            call_command("load_courses", "nonexistent.json")

    def test_missing_required_fields(self):
        """Test handling of JSON missing required fields"""

        test_data = [
            {
                "course_url": "https://test.edu/course",
                "departments": {"Computer Science": "https://test.edu/dept"},
                # Missing course_name and other required fields
            }
        ]

        with open("test_courses.json", "w") as f:
            json.dump(test_data, f)

        with self.assertRaises(KeyError):
            call_command("load_courses", "test_courses.json")

    def test_comprehensive_course_load(self):
        """Test loading complete course data with all relationships"""

        test_data = [
            {
                "course_url": "https://www.amherst.edu/academiclife/departments/courses/2425S/ANTH/ANTH-245-2425S",
                "course_name": "Medical Anthropology",
                "course_acronyms": ["ANTH-245"],
                "divisions": ["Humanities", "Social Sciences"],
                "departments": {
                    "Anthropology and Sociology": "https://www.amherst.edu/academiclife/departments/anthropology_sociology/courses"
                },
                "description": "The aim of this course is to introduce the ways that medical anthropologists understand illness...",
                "keywords": [
                    "Attention to Issues of Class",
                    "Attention to Issues of Gender and Sexuality",
                    "Attention to Issues of Race",
                    "Transnational or World Cultures Taught in English",
                ],
                "offerings": {
                    "Fall 2023": "https://www.amherst.edu/academiclife/departments/courses/2324F/ANTH/ANTH-245-2324F"
                },
            }
        ]

        with open("test_courses.json", "w") as f:
            json.dump(test_data, f)

        call_command("load_courses", "test_courses.json")

        # Verify course basic info
        course = Course.objects.first()
        self.assertEqual(course.courseName, "Medical Anthropology")
        self.assertTrue(course.courseDescription.startswith("The aim of this course"))
        self.assertEqual(
            course.courseLink,
            "https://www.amherst.edu/academiclife/departments/courses/2425S/ANTH/ANTH-245-2425S",
        )

        # Verify course code
        code = CourseCode.objects.first()
        self.assertEqual(code.value, "ANTH-245")
        self.assertIn(course, code.courses.all())

        # Verify departments
        dept = Department.objects.first()
        self.assertEqual(dept.name, "Anthropology and Sociology")
        self.assertIn(course, dept.courses.all())

        # Verify offerings
        self.assertEqual(course.fallOfferings.count(), 1)
        self.assertEqual(course.springOfferings.count(), 0)

        # Verify divisions
        self.assertEqual(course.divisions.count(), 2)
        self.assertIn(
            "Humanities", [division.name for division in course.divisions.all()]
        )
        self.assertIn(
            "Social Sciences", [division.name for division in course.divisions.all()]
        )

        # Verify keywords
        self.assertEqual(course.keywords.count(), 4)
        self.assertIn(
            "Attention to Issues of Race",
            [keyword.name for keyword in course.keywords.all()],
        )
