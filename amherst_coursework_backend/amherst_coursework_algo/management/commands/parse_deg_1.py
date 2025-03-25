from django.core.management.base import BaseCommand
from django.core.management import call_command
import os
import json
import logging

from amherst_coursework_backend.amherst_coursework_algo.parse_course_catalogue.parse_course_catalogue import (
    parse_all_courses,
    DATA_DIR,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Parse courses (first degree) from list of all courses in departments"

    def handle(self, *args, **options):
        try:
            # Create data directory if it doesn't exist
            os.makedirs(DATA_DIR, exist_ok=True)

            # Step 2: Parse all courses first degree
            logger.info("Starting step 2: Parsing courses (first degree)...")
            parsed_courses = parse_all_courses(testing_mode=False)
            if not parsed_courses:
                raise Exception("Failed to parse courses (first degree)")
            logger.info("Successfully completed step 2!")

        except Exception as e:
            logger.error(f"Error during parsing courses 1st degree: {str(e)}")
            raise
