"""
Get All Department Courses Command
===================================

This Django management command retrieves all course URLs for each department from the
Amherst College course catalog.

The command reads department information from a JSON file and scrapes each department's
page to collect all course URLs. The results are saved in a structured JSON format.

Example:
    To run this command::

        $ python manage.py get_all_department_courses

File Structure:
    Input:
        - department_catalogue_links.json:
            Contains department names and their course catalog URLs

    Output:
        - all_department_courses.json:
            Maps department names to lists of course URLs

Example Output Format::

    {
        "American Studies": [
            "https://www.amherst.edu/academiclife/departments/courses/2324F/AMST/AMST-111-2324F",
            "https://www.amherst.edu/academiclife/departments/courses/2324F/AMST/AMST-240-2324F"
        ],
        "Computer Science": [
            "https://www.amherst.edu/academiclife/departments/courses/2324F/COSC/COSC-111-2324F"
        ]
    }

Dependencies:
    - BeautifulSoup4 for HTML parsing
    - Requests for HTTP requests
    - Django for command infrastructure
"""

from django.core.management.base import BaseCommand
import os
import json
import logging

from amherst_coursework_algo.parse_course_catalogue.parse_course_catalogue import (
    get_all_department_courses,
    DATA_DIR,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Django management command to retrieve all course URLs by department.

    This command:
    1. Creates the data directory if it doesn't exist
    2. Reads department links from JSON
    3. Scrapes each department's course catalog page
    4. Collects all course URLs
    5. Saves results to JSON file

    Raises:
        FileNotFoundError: If department_catalogue_links.json is not found
        Exception: For other errors during execution
    """

    help = "Parse course catalog by department for list of all courses in departments"

    def handle(self, *args, **options):
        """Execute the command to retrieve all department course URLs.

        Args:
            *args: Variable length argument list
            **options: Arbitrary keyword arguments

        Raises:
            Exception: If department course retrieval fails

        Example:
            >>> python manage.py get_all_department_courses
            Starting step 1: Getting all department courses...
            Successfully completed step 1!
        """
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
