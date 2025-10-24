"""
Amherst Course Catalogue Parser
================================

This module provides functionality to scrape and parse course information from the
Amherst College course catalogue. It includes tools for handling HTTP requests,
parsing HTML content, and structuring course data.

The module implements a two-stage parsing process:
1. First degree parsing: Basic course information extraction
2. Second degree parsing: Enhanced parsing with section details

File Structure:
    Input Files:
        - department_catalogue_links.json:
            Base department URLs
        - all_department_courses.json:
            URLs for all courses by department
        - parsed_courses_detailed.json:
            First-degree parsed course data

    Output Files:
        - parsed_courses_second_deg.json:
            Final enhanced course information

Configuration:
    Environment Variables:
        - USER_AGENTS: Pipe-separated list of user agent strings
        - COURSE_BOT_EMAIL: Bot identifier email
        - COURSE_BOT_VERSION: Bot version number

Constants:
    - MAX_RETRIES: Maximum retry attempts for failed requests
    - TIMEOUT: Request timeout in seconds
    - REQUEST_DELAY: Delay between requests
    - EXCLUDED_COURSE_TYPES: Course types to skip

Example Usage:
    >>> from parse_course_catalogue import parse_all_courses_second_deg
    >>> enhanced_courses = parse_all_courses_second_deg()

Dependencies:
    - BeautifulSoup4 for HTML parsing
    - Requests for HTTP requests
    - python-dotenv for environment variables
"""

import time
from typing import Tuple
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import re
import json
from typing import List, Dict, Optional
import logging
import argparse
import os
from dotenv import load_dotenv
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for request handling
MAX_RETRIES = 5
TIMEOUT = 30  # seconds
BACKOFF_FACTOR = 0.6
REQUEST_DELAY = 1  # seconds
RETRY_DELAY_503 = 5  # seconds


DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "amherst_coursework_algo",
    "data",
    "course_catalogue",
)

DEPARTMENT_LINKS_PATH = os.path.join(DATA_DIR, "department_catalogue_links.json")
DEPARTMENT_COURSES_PATH = os.path.join(DATA_DIR, "all_department_courses.json")
LEVEL_1_PARSED_COURSES_PATH = os.path.join(DATA_DIR, "parsed_courses_detailed.json")
LEVEL_2_PARSED_COURSES_PATH = os.path.join(DATA_DIR, "parsed_courses_second_deg.json")

# Course types to exclude from the catalog (for now);
# later, to consider whether to consider, check out the catalogue AND
# https://www.amherst.edu/academiclife/departments
EXCLUDED_COURSE_TYPES = [
    "Courses of Instruction",
    "Bruss Seminar",
    "Kenan Colloquium",
    "Linguistics",
    "Mellon Seminar",
    "Physical Education",
    "Premedical Studies",
    "Teaching",
    "Five College Dance",
]


load_dotenv()


def get_request_headers() -> dict:
    """Generate secure request headers with request tracking.

    Returns:
        dict: Headers dictionary containing User-Agent and accept headers

    Raises:
        ValueError: If User-Agent configuration is invalid
    """

    USER_AGENTS = os.getenv("USER_AGENTS").split("|")

    default_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

    user_agent = default_agent

    user_agents_str = os.getenv("USER_AGENTS")
    if user_agents_str:
        user_agent = random.choice(USER_AGENTS)
        logger.info("Using user agents from environment variables")
    else:
        logger.warning("USER_AGENTS not found in environment, using default values")

    headers = {
        # Identify as a bot following robots.txt guidelines
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    # Validate headers
    if not headers["User-Agent"] or len(headers["User-Agent"]) < 10:
        logger.error("Invalid User-Agent configuration")
        raise ValueError("Invalid User-Agent configuration")

    return headers


def parse_department_catalogue(department_url: str) -> List[str]:
    """Parse a department page and extract course links.

    Args:
        department_url (str): URL of department course catalog page

    Returns:
        List[str]: List of course URLs found in the department page

    Example:
        >>> urls = parse_department_catalogue("https://www.amherst.edu/academiclife/departments/courses")
        >>> print(urls[0])
        'https://www.amherst.edu/academiclife/departments/courses/2324F/AMST/AMST-111'
    """
    headers = get_request_headers()

    try:
        logger.info(f"Fetching department page: {department_url}")
        response = requests.get(department_url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        course_list = soup.find("div", id="academics-course-list")

        if not course_list:
            logger.error(f"No course list found for {department_url}")
            return []

        course_links = []
        for course_div in course_list.find_all("div", class_="course-subj"):
            link = course_div.find("a")
            if link and link.get("href"):
                course_url = link["href"]
                if not course_url.startswith("http"):
                    course_url = "https://www.amherst.edu" + course_url
                course_links.append(course_url)

        logger.info(f"Found {len(course_links)} courses")
        return course_links

    except requests.RequestException as e:
        logger.error(f"Error fetching department page: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error parsing department page: {e}")
        return []


def get_all_department_courses():
    """Run parse_department_catalogue on all departments."""
    try:
        # Read department links from JSON file
        with open(
            DEPARTMENT_LINKS_PATH,
            "r",
        ) as f:
            departments = json.load(f)

        all_courses = {}

        # Parse each department's courses
        for dept in departments:
            dept_name = dept["name"]
            dept_url = dept["url"]
            logger.info(f"Processing department: {dept_name}")

            # Get course links for this department
            course_links = parse_department_catalogue(dept_url)
            all_courses[dept_name] = course_links

        # Save results to JSON file
        output_path = DEPARTMENT_COURSES_PATH
        with open(output_path, "w") as f:
            json.dump(all_courses, f, indent=4)

        logger.info(f"Saved department courses to {output_path}")
        return all_courses

    except FileNotFoundError:
        logger.error("Department links file not found")
        logger.info(DEPARTMENT_LINKS_PATH)
        return {}
    except Exception as e:
        logger.error(f"Error collecting all courses: {e}")
        return {}


# Helper function to find all siblings including text nodes
def find_next_siblings_with_text(tag, limit: int = -1):
    """Find siblings (including text nodes) that come after the given tag.

    Args:
        tag: The starting tag to find siblings from
        limit: Maximum number of siblings to return. -1 means no limit.

    Returns:
        List of siblings (Tags and text nodes)
    """
    current = tag.next_sibling
    siblings = []
    while current and (limit == -1 or len(siblings) < limit):
        if isinstance(current, (NavigableString, Tag)):
            # Only add non-empty text nodes
            if isinstance(current, NavigableString) and current.strip():
                siblings.append(current.strip())
            elif isinstance(current, Tag):
                siblings.append(current)
        current = current.next_sibling
    return siblings


def parse_course_first_deg(html_content: str, course_url: str) -> Optional[str]:
    """Parse basic course information from HTML content.

    Args:
        html_content (str): Raw HTML content of course page
        course_url (str): URL of the course page

    Returns:
        Optional[str]: JSON string containing parsed course data or None if parsing fails

    Example Output Format::
        {
            "course_url": "https://www.amherst.edu/...",
            "course_name": "Introduction to American Studies",
            "course_acronyms": ["AMST-111"],
            "divisions": ["Social Sciences"],
            "departments": {
                "American Studies": "https://www.amherst.edu/..."
            }
        }
    """
    try:
        if not html_content:
            logger.error("Empty HTML content provided")
            return None

        soup = BeautifulSoup(html_content, "html.parser")
        course_div = soup.find("div", id="academics-course-list")
        if not course_div:
            logger.error("Could not find course list div")
            return None

        soup = course_div

        # Extract basic info
        course_title = soup.find("h3")
        if not course_title:
            logger.error("Could not find course title (h3 tag)")
            return None
        course_name = course_title.text.strip()
        logger.debug(f"Successfully extracted course name: {course_name}")

        # Extract departments info
        dept_p = soup.find("p")
        while dept_p is not None and "Listed in:" not in dept_p.text:
            dept_p = dept_p.find_next("p")

        if not dept_p:
            logger.warning(
                "Department information not found, setting empty departments and acronyms"
            )
            departments, acronyms = {}, []
        else:
            departments = {}
            for a in dept_p.find_all("a"):
                link = a.get("href", "")
                if "https" not in link:
                    link = "https://www.amherst.edu" + link
                departments[a.text.strip()] = link

            acronyms = re.findall(r"[A-Z]+-\d+[A-Z]?", dept_p.text)

            if not departments:
                logger.warning("No departments found in department section")
            if not acronyms:
                logger.warning("No course acronyms found in department section")
            logger.debug(
                f"Found {len(departments)} departments and {len(acronyms)} acronyms"
            )

        # Extract course materials links
        materials_links = []
        materials_section = soup.find(
            "summary", string=lambda t: t and "Course Materials" in t
        )
        if materials_section:
            materials_div = materials_section.parent.find(
                "div", class_="details-wrapper"
            )
            if materials_div:
                for link in materials_div.find_all("a"):
                    href = link.get("href", "")
                    if href:
                        materials_links.append(href)
        else:
            materials_link = soup.find("a", string="Course Materials")
            if materials_link:
                href = materials_link.get("href", "")
                if href:
                    materials_links.append(href)

        if not materials_links:
            logger.warning("No course materials links found")
        else:
            logger.debug(f"Found {len(materials_links)} course material links")

        # Extract description
        desc_header = soup.find("h4", string="Description")
        if not desc_header:
            logger.warning("Description section not found, setting empty description")
            description = ""
        else:
            description = " ".join(
                [p.text.strip() for p in desc_header.find_next_siblings("p")]
            )
            if not description:
                logger.warning("Empty description found")
            else:
                logger.debug("Successfully extracted course description")

        # Extract times and location
        times_section = soup.find(
            "summary", string=lambda t: t and "Course times and locations" in t
        )
        if not times_section:
            logger.warning("Course times section not found, setting empty times_html")
            times_html = ""
        else:
            times_html = str(times_section.parent)
            if not times_html:
                logger.warning("Empty course times and locations found")
            else:
                logger.debug("Successfully extracted course times and locations")

        # Get professors information
        professors = []
        faculty_header = soup.find("h4", string="Faculty")

        if faculty_header:
            logger.debug("Found Faculty section header")
            faculty_p = faculty_header.find_next("p")

            if faculty_p:
                faculty_links = faculty_p.find_all("a")
                logger.debug(f"Found {len(faculty_links)} faculty links")

                for link in faculty_links:
                    try:
                        prof_name = link.text.strip()
                        prof_link = link["href"]
                        if not prof_link.startswith("http"):
                            prof_link = "https://www.amherst.edu" + prof_link

                        # Find the next text node after the link and look for section number(s)
                        # Handle both singular "Section" and plural "Sections"
                        # Also handle multiple sections like "Sections 01 and 01L"
                        next_text = link.next_sibling
                        sections = []
                        if next_text:
                            # Try to match single section: (Section 01)
                            section_match = re.search(r"\(Sections?\s*(\d+[A-Z]*)\)", next_text)
                            if section_match:
                                sections.append(section_match.group(1))
                            
                            # Try to match multiple sections: (Sections 01 and 01L)
                            multi_section_match = re.findall(r"(\d+[A-Z]*)", next_text)
                            if multi_section_match and len(multi_section_match) > 1:
                                sections = multi_section_match

                        # Create professor entry for each section
                        if sections:
                            for section in sections:
                                professors.append(
                                    {"name": prof_name, "link": prof_link, "section": section}
                                )
                        else:
                            # No section specified, add professor without section
                            professors.append(
                                {"name": prof_name, "link": prof_link, "section": None}
                            )
                        logger.debug(
                            f"Added professor: {prof_name} (Section: {section})"
                        )

                    except Exception as e:
                        logger.error(f"Error parsing professor link: {e}")
                        continue

            else:
                logger.warning(
                    "Faculty header found but no paragraph with professor information"
                )
        else:
            logger.debug(
                "No Faculty section found, attempting to extract from description"
            )
            prof_match = re.search(r"Professor (\w+)", description)
            if prof_match:
                prof_name = prof_match.group(1)
                professors.append({"name": prof_name, "link": None, "section": None})
                logger.debug(f"Extracted professor {prof_name} from description")
            else:
                logger.warning("No professor information found in description")

        if not professors:
            logger.warning("No professor information found for this course")

        # Extract divisions and keywords
        keywords_header = soup.find("h4", string="Keywords")
        divisions = []
        keywords = []
        if not keywords_header:
            logger.warning(
                "Keywords section not found, setting empty divisions and keywords"
            )
        else:
            keywords_p = keywords_header.find_next("p")
            if keywords_p:
                # Split content by <br> tag
                sections = [text for text in keywords_p.stripped_strings]

                for section in sections:
                    if "Divisions:" in section:
                        divisions = [
                            div.strip()
                            for div in section.split("Divisions:")[1].split(";")
                            if div.strip()
                        ]
                    else:
                        keywords = [
                            kw.strip() for kw in section.split(";") if kw.strip()
                        ]

                if not divisions:
                    logger.warning("No divisions found in keywords section")
                if not keywords:
                    logger.warning("No keywords found in keywords section")
                logger.debug(
                    f"Found {len(divisions)} divisions and {len(keywords)} keywords"
                )

        # Extract previous years offered
        offerings = {}
        offerings_text = []
        offerings_header = soup.find("h4", string="Offerings")
        if not offerings_header:
            logger.warning("Offerings section not found, setting empty offerings")
        else:
            for element in find_next_siblings_with_text(offerings_header):
                if isinstance(element, Tag) and element.name == "a":
                    text = element.text.strip()
                    if text:
                        link = element.get("href", "")
                        if "https" not in link:
                            link = "https://www.amherst.edu" + link
                        offerings[text] = link
                elif isinstance(element, str):
                    clean_text = element.replace("Other years:", "").replace(
                        "Offered in", ""
                    )

                    # Skip if the cleaned text contains only symbols
                    if not re.search(r"[a-zA-Z0-9]", clean_text):
                        continue

                    # Split by comma and clean each year
                    offerings_text = [
                        year.strip() for year in clean_text.split(",") if year.strip()
                    ]

                    if offerings_text:
                        for year in offerings_text:
                            offerings[year] = None

        if not offerings:
            logger.warning("No previous offerings found in offerings section")
        else:
            logger.debug(f"Found {len(offerings)} previous offerings")

        # Create JSON structure
        course_data = {
            "course_url": course_url,
            "course_name": course_name,
            "course_acronyms": acronyms,
            "divisions": divisions,
            "departments": departments,
            "professors": professors,
            "course_materials_links": materials_links,
            "description": description,
            "course_times_location": times_html,
            "keywords": keywords,
            "offerings": offerings,
        }

        # Validate required fields
        if not course_data["course_name"]:
            logger.error("Missing required field: course_name")
            return None

        logger.debug("Successfully parsed course data")
        return json.dumps(course_data, indent=2)

    except Exception as e:
        logger.error(f"Error parsing course: {str(e)}")
        return None


def create_session() -> requests.Session:
    """Create a requests session with retry logic"""
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_url_with_retry(url: str, session: requests.Session) -> Tuple[bool, str]:
    """Fetch URL content with retry logic"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        response = session.get(url, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        time.sleep(REQUEST_DELAY)  # Add delay between requests
        return True, response.text
    except Exception as e:
        logger.error(f"Error fetching {url}: {str(e)}")
        return False, ""


def save_incremental_results(output_path: str, all_courses: Dict):
    """Save results to JSON file incrementally."""
    with open(output_path, "w") as f:
        json.dump(all_courses, f, indent=4)
    logger.info(f"Saved incremental results to {output_path}")


def parse_all_courses(testing_mode: bool = False):
    """Parse all course pages using parse_course_first_deg."""
    output_path = LEVEL_1_PARSED_COURSES_PATH
    failed_urls = []

    try:
        # Load all department courses
        with open(DEPARTMENT_COURSES_PATH, "r") as f:
            departments = json.load(f)

        all_courses = {}
        session = create_session()
        total_courses = sum(len(courses) for courses in departments.values())
        processed = 0

        # Process each department
        for dept_name, course_urls in departments.items():
            logger.info(f"Processing department: {dept_name}")
            all_courses[dept_name] = []

            for url in course_urls:
                processed += 1
                logger.info(f"Processing course {processed}/{total_courses}: {url}")

                success, content = fetch_url_with_retry(url, session)
                if not success:
                    failed_urls.append((dept_name, url))
                    continue

                try:
                    course_data = parse_course_first_deg(content, url)
                    if course_data:
                        all_courses[dept_name].append(json.loads(course_data))
                        if testing_mode:
                            save_incremental_results(output_path, all_courses)
                except Exception as e:
                    logger.error(f"Error parsing course content for {url}: {e}")
                    failed_urls.append((dept_name, url))
                    continue

        # Retry failed URLs with longer delays
        if failed_urls:
            logger.info(f"Retrying {len(failed_urls)} failed URLs...")
            for dept_name, url in failed_urls:
                for retry in range(MAX_RETRIES):
                    time.sleep(RETRY_DELAY_503 * (retry + 1))  # Progressive delay
                    success, content = fetch_url_with_retry(url, session)
                    if success:
                        try:
                            course_data = parse_course_first_deg(content, url)
                            if course_data:
                                all_courses[dept_name].append(json.loads(course_data))
                                break
                        except Exception as e:
                            logger.error(
                                f"Error parsing course content for {url} on retry: {e}"
                            )

        save_incremental_results(output_path, all_courses)
        return all_courses

    except FileNotFoundError:
        logger.error("all_department_courses.json not found")
        return {}
    except Exception as e:
        logger.error(f"Error parsing courses: {e}")
        return {}


def parse_all_courses_second_deg():
    """Parse all courses to generate enhanced course information."""
    input_path = LEVEL_1_PARSED_COURSES_PATH
    output_path = LEVEL_2_PARSED_COURSES_PATH

    try:
        # Load existing first degree parsed courses
        with open(input_path, "r") as f:
            departments = json.load(f)

        # Initialize output structure
        enhanced_courses = {}

        total_depts = len(departments)
        for dept_idx, (dept_name, courses) in enumerate(departments.items(), 1):
            logger.info(f"Processing department {dept_idx}/{total_depts}: {dept_name}")

            enhanced_courses[dept_name] = []
            total_courses = len(courses)

            for course_idx, course in enumerate(courses, 1):
                logger.info(
                    f"Processing course {course_idx}/{total_courses} in {dept_name}"
                )

                try:
                    # Process course and add additional information
                    enhanced_course = parse_course_second_deg(course)
                    enhanced_courses[dept_name].append(enhanced_course)

                except Exception as e:
                    logger.error(
                        f"Error processing course {course.get('course_name', 'Unknown')}: {e}"
                    )
                    continue

            # Save results incrementally after each department
            with open(output_path, "w") as f:
                json.dump(enhanced_courses, f, indent=4)
            logger.debug(f"Saved incremental results for {dept_name}")

        logger.info(f"Completed second degree parsing. Results saved to {output_path}")
        return enhanced_courses

    except FileNotFoundError:
        logger.error(f"Input file {input_path} not found")
        return {}
    except Exception as e:
        logger.error(f"Error in parse_all_courses_second_deg: {e}")
        return {}


def parse_course_second_deg(course_data: dict) -> dict:
    """
    Parse additional course information and restructure data.

    Args:
        course_data (dict): Course data from first degree parsing

    Returns:
        dict: Enhanced course data with structured section information

    Example Output Format::
        {
            "course_name": "Introduction to American Studies",
            "section_information": {
                "1": {
                    "professor_name": "Professor Smith",
                    "course_location": "Webster 220",
                    "mon_start_time": "10:00 AM",
                    "mon_end_time": "11:20 AM"
                }
            }
        }
    """
    try:
        # Create deep copy to avoid modifying original
        enhanced_course = course_data.copy()

        # Initialize section information dictionary
        section_info = {}

        # Parse course times and location
        if course_data.get("course_times_location"):
            soup = BeautifulSoup(course_data["course_times_location"], "html.parser")

            # Find all section elements
            sections = soup.find_all("p")

            for section in sections:
                # Extract section number
                strong = section.find("strong")
                if strong:
                    section_num = strong.text.strip().replace("Section ", "")

                    # Initialize section info with all days set to null
                    section_info[section_num] = {
                        "professor_name": None,
                        "professor_link": None,
                        "course_location": None,
                        "course_materials_links": None,
                        "mon_start_time": None,
                        "mon_end_time": None,
                        "tue_start_time": None,
                        "tue_end_time": None,
                        "wed_start_time": None,
                        "wed_end_time": None,
                        "thu_start_time": None,
                        "thu_end_time": None,
                        "fri_start_time": None,
                        "fri_end_time": None,
                        "sat_start_time": None,
                        "sat_end_time": None,
                        "sun_start_time": None,
                        "sun_end_time": None,
                    }

                    # Get the original HTML content with <br> tags
                    section_html = str(section)

                    # Split by <br> tags and clean up
                    lines = re.split(r"<br\s*/?>", section_html)

                    # Skip the first line as it contains the section number
                    for line in lines[1:]:
                        # Clean HTML tags
                        clean_line = re.sub(r"<[^>]*>", "", line).strip()
                        if clean_line:
                            # Try to extract time and location
                            pattern = r"(M|Tu|W|Th|F|Sa|Su)[\s.]*(\d{1,2}:\d{2}\s*[AP]M)\s*-\s*(\d{1,2}:\d{2}\s*[AP]M)[\s.]*([A-Za-z0-9\s]+)"

                            match = re.search(pattern, clean_line)
                            if match:
                                days_str, start_time, end_time, location = (
                                    match.groups()
                                )

                                # Split days if multiple are listed
                                days = [d.strip() for d in re.split(r"[,/]", days_str)]

                                # Store the location
                                section_info[section_num][
                                    "course_location"
                                ] = location.strip()

                                # Map days to their respective fields
                                day_mapping = {
                                    "M": ("mon_start_time", "mon_end_time"),
                                    "Tu": ("tue_start_time", "tue_end_time"),
                                    "W": ("wed_start_time", "wed_end_time"),
                                    "Th": ("thu_start_time", "thu_end_time"),
                                    "F": ("fri_start_time", "fri_end_time"),
                                    "Sa": ("sat_start_time", "sat_end_time"),
                                    "Su": ("sun_start_time", "sun_end_time"),
                                }

                                # Update times for each day
                                for day in days:
                                    if day in day_mapping:
                                        start_field, end_field = day_mapping[day]
                                        section_info[section_num][
                                            start_field
                                        ] = start_time
                                        section_info[section_num][end_field] = end_time

        # Match professors to sections
        for prof in course_data.get("professors", []):
            section = prof.get("section")
            if section and section in section_info:
                section_info[section]["professor_name"] = prof["name"]
                section_info[section]["professor_link"] = prof["link"]

        # Match course materials links to sections
        for link in course_data.get("course_materials_links", []):
            section_match = re.search(r"section1=(\d+)", link)
            if section_match:
                section_num = section_match.group(1)
                if section_num in section_info:
                    section_info[section_num]["course_materials_links"] = link

        # Extract enrollment guidelines from description
        overGuidelines = {
            "text": "",
            "preferenceForMajor": False,
            "overallCap": 0,
            "freshmanCap": 0,
            "sophomoreCap": 0,
            "juniorCap": 0,
            "seniorCap": 0,
        }
        
        if course_data.get("description"):
            desc = course_data["description"]
            
            # Extract enrollment text
            enrollment_match = re.search(
                r"How to handle overenrollment:\s*([^\n]*?)(?=\s*Students who enroll|$)",
                desc,
                re.IGNORECASE
            )
            if enrollment_match:
                enrollment_text = enrollment_match.group(1).strip()
                # Handle "null" case
                if enrollment_text.lower() != "null" and enrollment_text:
                    overGuidelines["text"] = enrollment_text
                    
                    # Check for major preference
                    if re.search(r"major", enrollment_text, re.IGNORECASE):
                        overGuidelines["preferenceForMajor"] = True
                    
                    # Extract enrollment caps if present
                    cap_match = re.search(r"limited to (\d+)", enrollment_text, re.IGNORECASE)
                    if cap_match:
                        overGuidelines["overallCap"] = int(cap_match.group(1))
            
            # Clean up description - remove course offering text and enrollment text
            clean_desc = re.sub(r"^\([^)]*(?:Offered as|Listed as)[^)]*\)\s*", "", desc)
            # Remove enrollment guidelines from description
            clean_desc = re.sub(
                r"How to handle overenrollment:.*?(?=Students who enroll|Divisions:|$)",
                "",
                clean_desc,
                flags=re.IGNORECASE | re.DOTALL
            )
            enhanced_course["description"] = clean_desc.strip()

        # Update enhanced course data
        enhanced_course["section_information"] = section_info
        enhanced_course["overGuidelines"] = overGuidelines

        # Remove original fields that were restructured
        enhanced_course.pop("course_times_location", None)
        enhanced_course.pop("professors", None)
        enhanced_course.pop("course_materials_links", None)

        return enhanced_course

    except Exception as e:
        logger.error(f"Error in parse_course_second_deg: {str(e)}")
        return course_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse Amherst College course catalog")
    parser.add_argument(
        "--testing",
        action="store_true",
        help="Enable testing mode with incremental saves",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (default: WARNING)",
    )
    args = parser.parse_args()

    logger.setLevel(getattr(logging, args.log_level))
    parse_all_courses_second_deg()
