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
    return Course.objects.create(
        code="COSC111",
        title="Introduction to Computer Science",
        description="An introductory course to computer science.",
        department="COSC",
        professor="Prof. John Doe",
        keywords="computer science, programming, algorithms"
    )

