import pytest
from django.core.management import call_command
from django.test import TestCase
from unittest.mock import patch
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

        test_data = {
            "Computer Science": [  # Department name as key
                {
                    "course_url": "https://test.edu/course1",
                    "course_name": "Test Course 1",
                    "course_acronyms": ["COSC-101"],  # Valid course code format
                    "divisions": ["Humanities"],
                    "departments": {"Computer Science": "https://test.edu/dept1"},
                    "description": "Test course description",
                }
            ]
        }

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

        test_data = {
            "Computer Science": [
                {
                    "course_name": "Test Course",
                    "course_acronyms": ["COSC-101"],
                    "departments": {"Computer Science": "https://test.edu/dept"},
                    "offerings": {
                        "Fall 2023": "https://test.edu/fall2023",
                        "Spring 2024": "https://test.edu/spring2024",
                    },
                    "description": "Test course description",
                }
            ]
        }

        with open("test_courses.json", "w") as f:
            json.dump(test_data, f)

        call_command("load_courses", "test_courses.json")

        # Verify offerings were created
        course = Course.objects.first()
        self.assertEqual(course.fallOfferings.count(), 1)
        self.assertEqual(course.springOfferings.count(), 1)

    def test_load_course_with_professors(self):
        """Test loading course with professor data"""

        test_data = {
            "Test Department": [
                {
                    "course_name": "Test Course",
                    "course_acronyms": ["TEST-101"],
                    "departments": {"Computer Science": "https://test.edu/dept"},
                    "section_information": {
                        "01": {
                            "professor_name": "Dr. Test Professor",
                            "professor_link": "https://test.edu/prof1",
                        }
                    },
                    "description": "Test course description",
                }
            ]
        }

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

    def test_comprehensive_course_load(self):
        """Test loading complete course data with all relationships"""

        test_data = {
            "Anthropology and Sociology": [
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
        }

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

    def test_load_course_with_sections(self):
        """Test loading course with section data including meeting times"""

        test_data = {
            "Computer Science": [
                {
                    "course_name": "Test Course",
                    "course_acronyms": ["COSC-101"],
                    "departments": {"Computer Science": "https://test.edu/dept"},
                    "description": "Test course description",
                    "section_information": {
                        "01": {
                            "professor_name": "Dr. Test Professor",
                            "professor_link": "https://test.edu/prof1",
                            "course_location": "TEST 101",
                            "course_materials_links": "https://test.edu/materials",
                            "mon_start_time": "9:00 AM",
                            "mon_end_time": "9:50 AM",
                            "wed_start_time": "9:00 AM",
                            "wed_end_time": "9:50 AM",
                            "fri_start_time": "9:00 AM",
                            "fri_end_time": "9:50 AM",
                        },
                        "02": {
                            "professor_name": "Dr. Another Professor",
                            "professor_link": "https://test.edu/prof2",
                            "course_location": "TEST 102",
                            "mon_start_time": "10:00 AM",
                            "mon_end_time": "10:50 AM",
                            "wed_start_time": "10:00 AM",
                            "wed_end_time": "10:50 AM",
                            "fri_start_time": "10:00 AM",
                            "fri_end_time": "10:50 AM",
                        },
                    },
                }
            ]
        }

        with open("test_courses.json", "w") as f:
            json.dump(test_data, f)

        call_command("load_courses", "test_courses.json")

        # Verify course was created with sections
        course = Course.objects.first()
        self.assertEqual(course.sections.count(), 2)

        # Verify first section details
        section1 = course.sections.get(section_number="01")
        self.assertEqual(section1.professor.name, "Dr. Test Professor")
        self.assertEqual(section1.location, "TEST 101")
        self.assertEqual(section1.monday_start_time.strftime("%I:%M %p"), "09:00 AM")

        # Verify second section details
        section2 = course.sections.get(section_number="02")
        self.assertEqual(section2.professor.name, "Dr. Another Professor")
        self.assertEqual(section2.location, "TEST 102")
        self.assertEqual(section2.monday_start_time.strftime("%I:%M %p"), "10:00 AM")

        # Verify course materials link
        self.assertEqual(course.courseMaterialsLink, "https://test.edu/materials")

    def test_section_with_null_times(self):
        """Test loading section with null meeting times"""

        test_data = {
            "Computer Science": [
                {
                    "course_name": "Test Course",
                    "course_acronyms": ["COSC-101"],
                    "departments": {"Computer Science": "https://test.edu/dept"},
                    "description": "Test course description",
                    "section_information": {
                        "01": {
                            "professor_name": "Dr. Test Professor",
                            "course_location": "TEST 101",
                            "mon_start_time": None,
                            "mon_end_time": None,
                            "tue_start_time": "11:00 AM",
                            "tue_end_time": "12:15 PM",
                            "thu_start_time": "11:00 AM",
                            "thu_end_time": "12:15 PM",
                        }
                    },
                }
            ]
        }

        with open("test_courses.json", "w") as f:
            json.dump(test_data, f)

        call_command("load_courses", "test_courses.json")

        # Verify section times
        course = Course.objects.first()
        section = course.sections.first()
        self.assertIsNone(section.monday_start_time)
        self.assertIsNone(section.monday_end_time)
        self.assertEqual(section.tuesday_start_time.strftime("%I:%M %p"), "11:00 AM")
        self.assertEqual(section.thursday_end_time.strftime("%I:%M %p"), "12:15 PM")


class TestResolveDuplicatesCommand(TestCase):

    def _build_course(self, course_id, name, codes, departments):
        course = Course.objects.create(id=course_id, courseName=name)

        for code_value in codes:
            code, _ = CourseCode.objects.get_or_create(value=code_value)
            course.courseCodes.add(code)

        for dept_name, dept_code in departments:
            department, _ = Department.objects.get_or_create(
                name=dept_name,
                defaults={
                    "code": dept_code,
                    "link": f"https://test.edu/{dept_code.lower()}",
                },
            )
            course.departments.add(department)

        return course

    def test_merge_accepted_unions_codes_and_departments(self):
        self._build_course(
            4000101,
            "Duplicate Name",
            ["COSC-101"],
            [("Computer Science", "COSC")],
        )
        self._build_course(
            4000102,
            "Duplicate Name",
            ["MATH-101"],
            [("Mathematics", "MATH")],
        )

        with patch("builtins.input", return_value="y"):
            call_command("resolve_duplicates")

        self.assertEqual(Course.objects.filter(courseName="Duplicate Name").count(), 1)
        kept = Course.objects.get(courseName="Duplicate Name")
        self.assertEqual(kept.id, 4000101)
        self.assertSetEqual(
            {code.value for code in kept.courseCodes.all()}, {"COSC-101", "MATH-101"}
        )
        self.assertSetEqual(
            {dept.code for dept in kept.departments.all()}, {"COSC", "MATH"}
        )

    def test_merge_declined_keeps_both_courses(self):
        self._build_course(
            4000201,
            "Duplicate Name",
            ["COSC-201"],
            [("Computer Science", "COSC")],
        )
        self._build_course(
            4000202,
            "Duplicate Name",
            ["ENGL-201"],
            [("English", "ENGL")],
        )

        with patch("builtins.input", return_value="n"):
            call_command("resolve_duplicates")

        self.assertEqual(Course.objects.filter(courseName="Duplicate Name").count(), 2)

    def test_dry_run_makes_no_data_changes(self):
        self._build_course(
            4000301,
            "Duplicate Name",
            ["COSC-301"],
            [("Computer Science", "COSC")],
        )
        self._build_course(
            4000302,
            "Duplicate Name",
            ["STAT-301"],
            [("Statistics", "STAT")],
        )

        call_command("resolve_duplicates", "--yes", "--dry-run")

        self.assertEqual(Course.objects.filter(courseName="Duplicate Name").count(), 2)
        primary = Course.objects.get(id=4000301)
        self.assertSetEqual({code.value for code in primary.courseCodes.all()}, {"COSC-301"})
        self.assertSetEqual({dept.code for dept in primary.departments.all()}, {"COSC"})

    def test_group_larger_than_two_merges_all_into_first(self):
        self._build_course(
            4000401,
            "Duplicate Name",
            ["COSC-401"],
            [("Computer Science", "COSC")],
        )
        self._build_course(
            4000402,
            "Duplicate Name",
            ["MATH-401"],
            [("Mathematics", "MATH")],
        )
        self._build_course(
            4000403,
            "Duplicate Name",
            ["PHIL-401"],
            [("Philosophy", "PHIL")],
        )

        call_command("resolve_duplicates", "--yes")

        self.assertEqual(Course.objects.filter(courseName="Duplicate Name").count(), 1)
        kept = Course.objects.get(courseName="Duplicate Name")
        self.assertEqual(kept.id, 4000401)
        self.assertSetEqual(
            {code.value for code in kept.courseCodes.all()},
            {"COSC-401", "MATH-401", "PHIL-401"},
        )
        self.assertSetEqual(
            {dept.code for dept in kept.departments.all()},
            {"COSC", "MATH", "PHIL"},
        )

    def test_name_filter_only_processes_target_duplicate_name(self):
        self._build_course(
            4000501,
            "Target Name",
            ["COSC-501"],
            [("Computer Science", "COSC")],
        )
        self._build_course(
            4000502,
            "Target Name",
            ["MATH-501"],
            [("Mathematics", "MATH")],
        )

        self._build_course(
            4000503,
            "Other Name",
            ["ENGL-501"],
            [("English", "ENGL")],
        )
        self._build_course(
            4000504,
            "Other Name",
            ["PHYS-501"],
            [("Physics", "PHYS")],
        )

        call_command("resolve_duplicates", "--yes", "--name", "Target Name")

        self.assertEqual(Course.objects.filter(courseName="Target Name").count(), 1)
        self.assertEqual(Course.objects.filter(courseName="Other Name").count(), 2)
