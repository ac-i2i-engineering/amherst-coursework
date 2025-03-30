"""
Parse First Degree Course Information
=====================================

This Django management command parses detailed course information from the
Amherst College course catalog. It performs the first degree of parsing,
which extracts basic course details like name, description, professors, etc.

This command should be run after get_all_department_courses to process the
collected course URLs.

Example:
    To run this command::

        $ python manage.py parse_deg_1

File Dependencies:
    Input:
        - all_department_courses.json:
            Contains URLs of all courses by department
    
    Output:
        - parsed_courses_detailed.json:
            Contains detailed course information for each department

Example Output Format::

    {
        "American Studies": [
            {
                "course_url": "https://www.amherst.edu/...",
                "course_name": "Introduction to American Studies",
                "course_acronyms": ["AMST-111"],
                "divisions": ["Social Sciences"],
                "departments": {
                    "American Studies": "https://www.amherst.edu/..."
                },
                "professors": [
                    {
                        "name": "Professor Smith",
                        "link": "https://www.amherst.edu/...",
                        "section": "1"
                    }
                ],
                "description": "Course description text...",
                "keywords": ["Attention to Writing", "...]
            }
        ]
    }

Dependencies:
    - BeautifulSoup4 for HTML parsing
    - Requests for HTTP requests
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
import os
import json
import logging

from amherst_coursework_algo.parse_course_catalogue.parse_course_catalogue import (
    parse_all_courses,
    DATA_DIR,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Django management command to parse detailed course information.
    
    This command performs the first level of parsing on course pages, extracting
    basic information like course names, descriptions, professors, and other
    metadata.

    Note:
        This command should be run after get_all_department_courses to ensure
        the required input file exists.
    """

    help = "Parse courses (first degree) from list of all courses in departments"

    def handle(self, *args, **options):
        """Execute the command to parse first-degree course information.
        
        Args:
            *args: Variable length argument list
            **options: Arbitrary keyword arguments
        
        Raises:
            Exception: If course parsing fails or required files are missing
            
        Example:
            >>> python manage.py parse_deg_1
            Starting step 2: Parsing courses (first degree)...
            Successfully completed step 2!
        """
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
