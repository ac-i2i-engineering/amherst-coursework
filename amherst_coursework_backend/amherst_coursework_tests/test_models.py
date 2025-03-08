# test_models.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import time
from amherst_coursework_algo.models import (
    Course,
    CourseCode,
    Department,
    PrerequisiteSet,
    Professor,
    Section,
    Year,
)


class CourseModelTest(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="Computer Science", code="COSC", link="https://www.amherst.edu/cs"
        )
        self.course = Course.objects.create(
            id=5140111,
            courseName="Intro to Computer Science",
            courseDescription="Learn to code",
            credits=4,
        )
        self.course_code = CourseCode.objects.create(value="COSC-111")

    def test_course_creation(self):
        self.assertEqual(self.course.courseName, "Intro to Computer Science")
        self.assertEqual(self.course.credits, 4)

    def test_course_relationships(self):
        self.course.departments.add(self.department)
        self.course.courseCodes.add(self.course_code)
        self.assertEqual(self.course.departments.first(), self.department)
        self.assertEqual(self.course.courseCodes.first(), self.course_code)

    def test_invalid_course_id(self):
        with self.assertRaises(ValidationError):
            Course.objects.create(
                id=99999999, courseName="Test Course"  # Invalid ID - more than 7 digits
            ).full_clean()

    def test_enrollment_caps_validation(self):
        course = Course.objects.create(
            id=5140112, courseName="Test Course", overallCap=20
        )

        # Test valid caps
        course.freshmanCap = 10
        course.sophomoreCap = 10
        course.juniorCap = 10
        course.seniorCap = 10
        course.full_clean()  # Should not raise error

        # Test invalid cap
        course.freshmanCap = 25  # Exceeds overall cap
        with self.assertRaises(ValidationError):
            course.full_clean()

    def test_prerequisites(self):
        prereq_course = Course.objects.create(id=5140110, courseName="Prereq Course")
        prereq_set = PrerequisiteSet.objects.create(prerequisite_for=self.course)
        prereq_set.courses.add(prereq_course)
        prereq_set.save()

        self.course.recommended_courses.add(prereq_course)

        self.assertIn(prereq_set, self.course.required_courses.all())
        self.assertEqual(self.course.recommended_courses.first(), prereq_course)


class DepartmentModelTest(TestCase):
    def test_department_creation(self):
        dept = Department.objects.create(
            name="Mathematics", code="MATH", link="https://www.amherst.edu/math"
        )
        self.assertEqual(str(dept), "Mathematics")

    def test_invalid_code_length(self):
        with self.assertRaises(ValidationError):
            Department.objects.create(
                name="Biology", code="BIO", link="https://example.com"  # Too short
            ).full_clean()


class SectionModelTest(TestCase):
    def setUp(self):
        self.professor = Professor.objects.create(
            name="John Doe", link="https://faculty.amherst.edu/jdoe"
        )
        self.course = Course.objects.create(id=5140111, courseName="Intro to Computer Science")

    def test_section_creation(self):
        section = Section.objects.create(
            section_number="01",
            section_for=self.course,
            monday_start_time=time(9, 0),
            monday_end_time=time(9, 50),
            wednesday_start_time=time(9, 0), 
            wednesday_end_time=time(9, 50),
            friday_start_time=time(9, 0),
            friday_end_time=time(9, 50),
            location="MERR 131",
            professor=self.professor,
        )
        self.assertEqual(str(section), "01 for Intro to Computer Science")

    def test_invalid_section_number(self):
        with self.assertRaises(ValidationError):
            Section.objects.create(
                section_number="1", # Invalid format - needs 2 digits
                section_for=self.course,
                monday_start_time=time(9, 0),
                monday_end_time=time(9, 50),
                location="MERR 131", 
                professor=self.professor,
            ).full_clean()

    def test_invalid_time_order(self):
        with self.assertRaises(ValidationError):
            Section.objects.create(
                section_number="01",
                section_for=self.course, 
                monday_start_time=time(10, 0),
                monday_end_time=time(9, 0),  # End before start
                location="MERR 131",
                professor=self.professor,
            ).full_clean()

    def test_section_with_lab(self):
        section = Section.objects.create(
            section_number="01L", # Valid lab section
            section_for=self.course,
            thursday_start_time=time(13, 0),
            thursday_end_time=time(15, 50),
            location="MERR 131",
            professor=self.professor,
        )
        self.assertEqual(str(section), "01L for Intro to Computer Science")



class YearModelTest(TestCase):
    def test_year_creation(self):
        year = Year.objects.create(year=2024, link="https://catalog.amherst.edu/2024")
        self.assertEqual(str(year), "2024")

    def test_invalid_year(self):
        with self.assertRaises(ValidationError):
            Year.objects.create(year=1800).full_clean()  # Before minimum year


class ProfessorModelTest(TestCase):
    def test_professor_creation(self):
        professor = Professor.objects.create(
            name="Jane Smith", link="https://faculty.amherst.edu/jsmith"
        )
        self.assertEqual(str(professor), "Jane Smith")
        self.assertEqual(professor.link, "https://faculty.amherst.edu/jsmith")


class CourseCodeModelTest(TestCase):
    def test_course_code_creation(self):
        code = CourseCode.objects.create(value="COSC-111")
        self.assertEqual(str(code), "COSC-111")

    def test_invalid_code_length(self):
        with self.assertRaises(ValidationError):
            CourseCode.objects.create(value="CS1").full_clean()  # Too short
