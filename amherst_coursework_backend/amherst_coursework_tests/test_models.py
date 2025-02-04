# test_models.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import time
from amherst_coursework_algo.models import (
    Course, CourseCode, Department, OverGuidelines,
    Prerequisites, PrerequisiteSet, Professor, Section, Year
)

class CourseModelTest(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="Computer Science",
            code="COSC",
            link="https://www.amherst.edu/cs"
        )
        self.course = Course.objects.create(
            id=5140111,
            courseName="Intro to Computer Science",
            courseDescription="Learn to code",
            credits=4
        )
        self.course_code = CourseCode.objects.create(value="COSC111")
        
    def test_course_creation(self):
        self.assertEqual(self.course.courseName, "Intro to Computer Science")
        self.assertEqual(self.course.credits, 4)

    def test_course_relationships(self):
        self.course.department.add(self.department)
        self.course.courseCodes.add(self.course_code)
        self.assertEqual(self.course.department.first(), self.department)
        self.assertEqual(self.course.courseCodes.first(), self.course_code)

    def test_invalid_course_id(self):
        with self.assertRaises(ValidationError):
            Course.objects.create(
                id=99999999,  # Invalid ID
                courseName="Test Course"
            ).full_clean()

class DepartmentModelTest(TestCase):
    def test_department_creation(self):
        dept = Department.objects.create(
            name="Mathematics",
            code="MATH",
            link="https://www.amherst.edu/math"
        )
        self.assertEqual(str(dept), "Mathematics")

    def test_invalid_code_length(self):
        with self.assertRaises(ValidationError):
            Department.objects.create(
                name="Biology",
                code="BIO",  # Too short
                link="https://example.com"
            ).full_clean()

class SectionModelTest(TestCase):
    def setUp(self):
        self.professor = Professor.objects.create(
            name="John Doe",
            link="https://faculty.amherst.edu/jdoe"
        )
        self.course = Course.objects.create(
            id=5140111,
            courseName="Test Course"
        )

    def test_section_creation(self):
        section = Section.objects.create(
            section_number=1,
            myCourse=self.course,
            days="MWF",
            start_time=time(9, 0),
            end_time=time(9, 50),
            location="MERR 131",
            professor=self.professor
        )
        self.assertEqual(str(section), "MWF 09:00:00-09:50:00 in MERR 131")

    def test_invalid_days(self):
        with self.assertRaises(ValidationError):
            Section.objects.create(
                section_number=1,
                myCourse=self.course,
                days="XYZ",  # Invalid days
                start_time=time(9, 0),
                end_time=time(9, 50),
                location="MERR 131",
                professor=self.professor
            ).full_clean()

    def test_invalid_time_order(self):
        with self.assertRaises(ValidationError):
            Section.objects.create(
                section_number=1,
                myCourse=self.course,
                days="MWF",
                start_time=time(10, 0),
                end_time=time(9, 0),  # End before start
                location="MERR 131",
                professor=self.professor
            ).full_clean()

class OverGuidelinesModelTest(TestCase):
    def setUp(self):
        self.course = Course.objects.create(
            id=5140111,
            courseName="Test Course"
        )

    def test_cap_validation(self):
        with self.assertRaises(ValidationError):
            OverGuidelines.objects.create(
                myCourse=self.course,
                text="Test guidelines",
                overallCap=20,
                freshmanCap=25  # Exceeds overall cap
            ).full_clean()

class PrerequisitesModelTest(TestCase):
    def setUp(self):
        self.course = Course.objects.create(
            id=5140111,
            courseName="Advanced Course"
        )
        self.prereq_course = Course.objects.create(
            id=5140110,
            courseName="Intro Course"
        )

    def test_prerequisites_creation(self):
        prereq_set = PrerequisiteSet.objects.create()
        prereq_set.courses.add(self.prereq_course)
        
        prerequisites = Prerequisites.objects.create(
            description="Must complete intro course",
            professor_override=True
        )
        prerequisites.required_courses.add(prereq_set)
        prerequisites.recommended_courses.add(self.prereq_course)
        
        self.assertEqual(prerequisites.required_courses.first(), prereq_set)
        self.assertTrue(prerequisites.professor_override)

class YearModelTest(TestCase):
    def test_year_creation(self):
        year = Year.objects.create(
            year=2024,
            link="https://catalog.amherst.edu/2024"
        )
        self.assertEqual(str(year), "2024")

    def test_invalid_year(self):
        with self.assertRaises(ValidationError):
            Year.objects.create(
                year=1800  # Before minimum year
            ).full_clean()

class ProfessorModelTest(TestCase):
    def test_professor_creation(self):
        professor = Professor.objects.create(
            name="Jane Smith",
            link="https://faculty.amherst.edu/jsmith"
        )
        self.assertEqual(str(professor), "Jane Smith")
        self.assertEqual(professor.link, "https://faculty.amherst.edu/jsmith")

class CourseCodeModelTest(TestCase):
    def test_course_code_creation(self):
        code = CourseCode.objects.create(value="COSC111")
        self.assertEqual(str(code), "COSC111")

    def test_invalid_code_length(self):
        with self.assertRaises(ValidationError):
            CourseCode.objects.create(
                value="CS1"  # Too short
            ).full_clean()