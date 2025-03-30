"""
Parse Second Degree Course Information
=======================================

This Django management command performs detailed parsing of course information from the
Amherst College course catalog. It executes the second degree of parsing, which extracts
and structures additional details like section times, locations, and professor assignments.

This command should be run after parse_deg_1 to enhance the initially parsed course data.

Example:
    To run this command::

        $ python manage.py parse_deg_2

File Dependencies:
    Input:
        - parsed_courses_detailed.json:
            Contains basic course information from first degree parsing
    
    Output:
        - parsed_courses_second_deg.json:
            Contains enhanced course information with structured section data

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
                "section_information": {
                    "1": {
                        "professor_name": "Professor Smith",
                        "professor_link": "https://www.amherst.edu/...",
                        "course_location": "Webster 220",
                        "mon_start_time": "10:00 AM",
                        "mon_end_time": "11:20 AM",
                        "wed_start_time": "10:00 AM",
                        "wed_end_time": "11:20 AM"
                    }
                },
                "description": "Course description text...",
                "keywords": ["Attention to Writing", "..."]
            }
        ]
    }

Dependencies:
    - BeautifulSoup4 for HTML parsing
    - JSON for data handling
"""

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
    """Django management command to enhance course information with section details.
    
    This command performs the second level of parsing, which:
    1. Reads the basic course information from first degree parsing
    2. Extracts detailed section information including times and locations
    3. Structures professor assignments and course materials by section
    4. Cleans and enhances course descriptions
    
    Note:
        This command should be run after parse_deg_1 to ensure the required
        input file exists with basic course information.
    """

    help = "Parse courses (second degree) from list of all courses in departments"

    def handle(self, *args, **options):
        """Execute the command to parse second-degree course information.
        
        Args:
            *args: Variable length argument list
            **options: Arbitrary keyword arguments
        
        Raises:
            Exception: If course enhancement fails or required files are missing
            
        Example:
            >>> python manage.py parse_deg_2
            Starting step 3: Parsing courses (second degree)...
            Successfully completed step 3!
        """
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
