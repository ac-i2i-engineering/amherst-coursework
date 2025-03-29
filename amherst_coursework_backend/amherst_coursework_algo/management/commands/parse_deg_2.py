from django.core.management.base import BaseCommand
from django.core.management import call_command
import os
import json
import logging

from amherst_coursework_algo.parse_course_catalogue.parse_course_catalogue import (
    parse_all_courses_second_deg,
    DATA_DIR,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Parse courses (second degree) from list of all courses in departments"

    def handle(self, *args, **options):
        try:
            # Create data directory if it doesn't exist
            os.makedirs(DATA_DIR, exist_ok=True)

            # Step 3: Parse all courses second degree
            logger.info("Starting step 3: Parsing courses (second degree)...")
            enhanced_courses = parse_all_courses_second_deg()
            if not enhanced_courses:
                raise Exception("Failed to parse courses (second degree)")
            logger.info("Successfully completed step 3!")

        except Exception as e:
            logger.error(f"Error during parsing courses degree 2: {str(e)}")
            raise
