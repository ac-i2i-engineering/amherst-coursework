"""
Course Parser Setup Command
============================

This module provides a Django management command to setup course parsing by creating
semester-specific department catalog links from a base file.

The command reads a base JSON file containing department links and modifies them to
include the current semester identifier in the URLs.

Example:
    To run this command::

        $ python manage.py course_parser_setup

Configuration:
    - SEMESTER: Global variable defining the current semester (e.g., "2526F")
    - BASE_DIR: Directory containing course catalog data
    - BASE_JSON_PATH: Path to the base department links file
    - TARGET_JSON_PATH: Path where the modified file will be saved
"""

from django.core.management.base import BaseCommand
import os
import json
import logging
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global semester variable - can be modified as needed
SEMESTER = "2526S"  # Example: 2324F for Fall 2023 semester, 2324S for Spring 2024

BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "course_catalogue",
)

BASE_JSON_PATH = os.path.join(BASE_DIR, "department_catalogue_links_base.json")
TARGET_JSON_PATH = os.path.join(BASE_DIR, "department_catalogue_links.json")


class Command(BaseCommand):
    """
    Django management command to prepare department catalog links for course parsing.

    This command reads department links from a base JSON file and modifies them to include
    the current semester identifier in the URLs. The modified links are then saved to a
    new JSON file for use by the course parser.

    Attributes:
        help (str): Brief command description shown in manage.py help

    File Structure:
        - Input: department_catalogue_links_base.json
            Contains base URLs for department course pages
        - Output: department_catalogue_links.json
            Contains URLs modified to include current semester
    """

    help = "Create semester-specific department catalog links from base file"

    def handle(self, *args, **options):
        """
        Execute the command to create semester-specific department catalog links.

        Args:
            *args: Variable length argument list
            **options: Arbitrary keyword arguments

        Raises:
            FileNotFoundError: If the base JSON file is not found
            Exception: For other errors during execution

        Example JSON structure::

            [
                {
                    "name": "American Studies",
                    "url": "https://www.amherst.edu/academiclife/departments/american_studies/courses"
                }
            ]
        """
        try:

            # Read the base JSON file
            with open(BASE_JSON_PATH, "r") as file:
                departments = json.load(file)

            # Modify URLs to include semester
            modified_departments = []
            for dept in departments:
                dept_copy = dept.copy()  # Create a copy to avoid modifying the original
                dept_copy["url"] = f"{dept['url']}/{SEMESTER}"
                modified_departments.append(dept_copy)

            # Write to the target JSON file
            with open(TARGET_JSON_PATH, "w") as file:
                json.dump(modified_departments, file, indent=4)

            logger.info(
                f"Successfully created {TARGET_JSON_PATH} with semester {SEMESTER}"
            )

        except FileNotFoundError:
            logger.error(f"Base file not found: {BASE_JSON_PATH}")
            raise
        except Exception as e:
            logger.error(f"Error updating department links: {str(e)}")
            raise
