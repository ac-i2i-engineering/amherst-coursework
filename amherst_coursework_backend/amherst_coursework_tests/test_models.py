import pytest
from unittest import mock
from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.test import TestCase
from amherst_coursework_algo.models import Course


class CourseModelTest(TestCase):

    @pytest.fixture(autouse=True)
    def _setup(self, course):
        self.course = course

    def test_course_creation(self):
        self.assertEqual(self.course.code, "COSC111")
        self.assertEqual(self.course.title, "Introduction to Computer Science")
        self.assertEqual(
            self.course.description, "An introductory course to computer science."
        )
        self.assertEqual(self.course.department, "COSC")
        self.assertEqual(self.course.professor, "Prof. John Doe")
        self.assertEqual(
            self.course.keywords, "computer science, programming, algorithms"
        )
        self.assertEqual(list(self.course.prerequisites.all()), [])
        self.assertEqual(self.course.how_to_handle_overenrollment, None)
        self.assertEqual(self.course.enrollment_limit, 20)
        self.assertEqual(self.course.credit_hours, 4)

    def test_course_str(self):
        self.assertEqual(str(self.course), "COSC111: Introduction to Computer Science")
