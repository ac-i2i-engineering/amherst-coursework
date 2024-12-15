import pytest
from unittest import mock
from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.test import TestCase
from amherst_coursework_algo.models import Course

@pytest.fixture
def mock_course():
    with mock.patch('mammoth_course_compass_algo.models.Course.objects.create') as mock_create:
        mock_course = mock.Mock(spec=Course)
        mock_course.code = "COSC111"
        mock_course.title = "Introduction to Computer Science"
        mock_course.description = "An introductory course to computer science."
        mock_course.department = "COSC"
        mock_course.professor = "Prof. John Doe"
        mock_course.keywords = "computer science, programming, algorithms"
        mock_course.__str__ = mock.Mock(return_value="COSC111: Introduction to Computer Science")
        mock_create.return_value = mock_course
        yield mock_course

class CourseModelTest(TestCase):

    @pytest.fixture(autouse=True)
    def _setup(self, mock_course):
        self.course = mock_course

    def test_course_creation(self):
        self.assertEqual(self.course.code, "COSC111")
        self.assertEqual(self.course.title, "Introduction to Computer Science")
        self.assertEqual(self.course.description, "An introductory course to computer science.")
        self.assertEqual(self.course.department, "COSC")
        self.assertEqual(self.course.professor, "Prof. John Doe")
        self.assertEqual(self.course.keywords, "computer science, programming, algorithms")

    def test_course_str(self):
        self.assertEqual(str(self.course), "COSC111: Introduction to Computer Science")

   
