from django.core.management.base import BaseCommand
from django.core.management import call_command
import os
import json
import logging

from amherst_coursework_algo.management.commands.parse_course_catalogue import (
    get_all_department_courses,
    parse_all_courses,
    parse_all_courses_second_deg,
    DATA_DIR,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Parse course catalog and load courses into database"

    def handle(self, *args, **options):
        try:
            # Create data directory if it doesn't exist
            os.makedirs(DATA_DIR, exist_ok=True)

            # Step 1: Get all department courses
            logger.info("Starting step 1: Getting all department courses...")
            department_courses = get_all_department_courses()
            if not department_courses:
                raise Exception("Failed to get department courses")

            # Step 2: Parse all courses first degree
            logger.info("Starting step 2: Parsing courses (first degree)...")
            parsed_courses = parse_all_courses(testing_mode=False)
            if not parsed_courses:
                raise Exception("Failed to parse courses (first degree)")

            # Step 3: Parse all courses second degree
            logger.info("Starting step 3: Parsing courses (second degree)...")
            enhanced_courses = parse_all_courses_second_deg()
            if not enhanced_courses:
                raise Exception("Failed to parse courses (second degree)")

            # Step 4: Load courses into database
            logger.info("Starting step 4: Loading courses into database...")
            final_output_path = os.path.join(DATA_DIR, "parsed_courses_second_deg.json")
            if not os.path.exists(final_output_path):
                raise Exception(f"Parsed courses file not found at {final_output_path}")

            call_command("load_courses", final_output_path)
            logger.info("Successfully completed all steps!")

        except Exception as e:
            logger.error(f"Error during execution: {str(e)}")
            raise

    def add_arguments(self, parser):
        # Add any command line arguments here if needed
        pass
