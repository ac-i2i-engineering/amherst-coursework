import os
import sys
import django
import pytest

def pytest_configure():
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'amherst_coursework_backend.settings')
    django.setup()

@pytest.fixture
def course(db):
    from amherst_coursework_algo.models import Course
    course = Course.objects.create(
        code="COSC111",
        title="Introduction to Computer Science",
        description="An introductory course to computer science.",
        department="COSC",
        professor="Prof. John Doe",
        keywords="computer science, programming, algorithms",
        how_to_handle_overenrollment=None,
        enrollment_limit=20,
        credit_hours=4
    )
    course.prerequisites.set([])
    return course

