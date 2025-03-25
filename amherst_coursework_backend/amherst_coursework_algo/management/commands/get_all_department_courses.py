from django.core.management.base import BaseCommand
from django.core.management import call_command
import os
import json
import logging

from amherst_coursework_backend.amherst_coursework_algo.parse_course_catalogue.parse_course_catalogue import (
    get_all_department_courses,
    DATA_DIR,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Parse course catalog by department for list of all courses in departments"

    def handle(self, *args, **options):
        try:
            # Create data directory if it doesn't exist
            os.makedirs(DATA_DIR, exist_ok=True)

            # Step 1: Get all department courses
            logger.info("Starting step 1: Getting all department courses...")
            department_courses = get_all_department_courses()
            if not department_courses:
                raise Exception("Failed to get department courses")
            logger.info("Successfully completed step 1!")

        except Exception as e:
            logger.error(f"Error during getting all department courses: {str(e)}")
            raise
