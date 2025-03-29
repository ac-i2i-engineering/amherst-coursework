from django.core.management.base import BaseCommand
import os
import json
import logging
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global semester variable - can be modified as needed
SEMESTER = "2526F"  # Example: 2324F for Fall 2023 semester, 2324S for Spring 2024

BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "course_catalogue",
)

BASE_JSON_PATH = os.path.join(BASE_DIR, "department_catalogue_links_base.json")
TARGET_JSON_PATH = os.path.join(BASE_DIR, "department_catalogue_links.json")


class Command(BaseCommand):
    help = "Create semester-specific department catalog links from base file"

    def handle(self, *args, **options):
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
