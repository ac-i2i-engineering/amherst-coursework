# TODO: Run the algo on all departments and manually go through the outputs

import time
import html
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for request handling
MAX_RETRIES = 5
TIMEOUT = 30  # seconds
BACKOFF_FACTOR = 0.6
REQUEST_DELAY = 1  # seconds
RETRY_DELAY_503 = 5  # seconds

# Course types to exclude from the catalog (for now);
# later, to consider whether to consider, check out the catelogue AND 
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
    "Five College Dance"
]

def parse_department_catelogue(department_url: str) -> List[str]:
    """Parse a department page and extract course links."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    }
    
    try:
        logger.info(f"Fetching department page: {department_url}")
        response = requests.get(department_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        course_list = soup.find('div', id='academics-course-list')
        
        if not course_list:
            logger.error(f"No course list found for {department_url}")
            return []
        
        course_links = []
        for course_div in course_list.find_all('div', class_='course-subj'):
            link = course_div.find('a')
            if link and link.get('href'):
                course_url = link['href']
                if not course_url.startswith('http'):
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
    """Run parse_department_catelogue on all departments."""
    try:
        # Read department links from JSON file
        with open('course_catelogue_scraper/parsing_results/department_catelogue_links.json', 'r') as f:
            departments = json.load(f)
        
        all_courses = {}
        
        # Parse each department's courses
        for dept in departments:
            dept_name = dept['name']
            dept_url = dept['url']
            logger.info(f"Processing department: {dept_name}")
            
            # Get course links for this department
            course_links = parse_department_catelogue(dept_url)
            all_courses[dept_name] = course_links
            
        # Save results to JSON file
        output_path = 'course_catelogue_scraper/parsing_results/all_department_courses.json'
        with open(output_path, 'w') as f:
            json.dump(all_courses, f, indent=4)
            
        logger.info(f"Saved department courses to {output_path}")
        return all_courses
            
    except FileNotFoundError:
        logger.error("Department links file not found")
        return {}
    except Exception as e:
        logger.error(f"Error collecting all courses: {e}")
        return {}

# Helper function to find all siblings including text nodes
def find_next_siblings_with_text(tag):
    """Find all siblings (including text nodes) that come after the given tag."""
    current = tag.next_sibling
    siblings = []
    while current:
        if isinstance(current, (NavigableString, Tag)):
            # Only add non-empty text nodes
            if isinstance(current, NavigableString) and current.strip():
                siblings.append(current.strip())
            elif isinstance(current, Tag):
                siblings.append(current)
        current = current.next_sibling
    return siblings

def parse_course_first_deg(html_content, course_url) -> Optional[str]:
    try:
        if not html_content:
            logger.error("Empty HTML content provided")
            return None
            
        soup = BeautifulSoup(html_content, 'html.parser')
        course_div = soup.find('div', id='academics-course-list')
        if not course_div:
            logger.error("Could not find course list div")
            return None
        
        soup = course_div
        
        # Extract basic info
        course_title = soup.find('h3')
        if not course_title:
            logger.error("Could not find course title (h3 tag)")
            return None
        course_name = course_title.text.strip()
        logger.debug(f"Successfully extracted course name: {course_name}")
        
        # Extract departments info
        dept_p = soup.find('p')
        while dept_p is not None and "Listed in:" not in dept_p.text:
            dept_p = dept_p.find_next('p')

        if not dept_p:
            logger.warning("Department information not found, setting empty departments and acronyms")
            departments, acronyms = {}, []
        else:
            departments = {}
            for a in dept_p.find_all('a'):
                link = a.get('href', '')
                if "https" not in link:
                    link = "https://www.amherst.edu" + link
                departments[a.text.strip()] = link
            acronyms = re.findall(r'[A-Z]+-\d+', dept_p.text)
            
            if not departments:
                logger.warning("No departments found in department section")
            if not acronyms:
                logger.warning("No course acronyms found in department section")
            logger.debug(f"Found {len(departments)} departments and {len(acronyms)} acronyms")
        
        # Extract course materials links
        materials_links = []
        materials_section = soup.find('summary', string=lambda t: t and 'Course Materials' in t)
        if materials_section:
            materials_div = materials_section.parent.find('div', class_='details-wrapper')
            if materials_div:
                for link in materials_div.find_all('a'):
                    href = link.get('href', '')
                    if href:
                        materials_links.append(href)
        else:
            materials_link = soup.find('a', string='Course Materials')
            if materials_link:
                href = materials_link.get('href', '')
                if href:
                    materials_links.append(href)
                
        if not materials_links:
            logger.warning("No course materials links found")
        else:
            logger.debug(f"Found {len(materials_links)} course material links")
        
        # Extract description
        desc_header = soup.find('h4', string='Description')
        if not desc_header:
            logger.warning("Description section not found, setting empty description")
            description = ""
        else:
            description = ' '.join([p.text.strip() for p in desc_header.find_next_siblings('p')])
            if not description:
                logger.warning("Empty description found")
            else:
                logger.debug("Successfully extracted course description")
        
        # Extract times and location
        times_section = soup.find('summary', string=lambda t: t and 'Course times and locations' in t)
        if not times_section:
            logger.warning("Course times section not found, setting empty times_html")
            times_html = ""
        else:
            times_html = str(times_section.parent)
            if not times_html:
                logger.warning("Empty course times and locations found")
            else:
                logger.debug("Successfully extracted course times and locations")

        # Extract divisions and keywords
        keywords_header = soup.find('h4', string='Keywords')
        divisions = []
        keywords = []
        if not keywords_header:
            logger.warning("Keywords section not found, setting empty divisions and keywords")
        else:
            keywords_p = keywords_header.find_next('p')
            if keywords_p:
                # Split content by <br> tag
                sections = [text for text in keywords_p.stripped_strings]
                
                for section in sections:
                    if 'Divisions:' in section:
                        divisions = [div.strip() for div in section.split('Divisions:')[1].split(';') if div.strip()]
                    else:
                        keywords = [kw.strip() for kw in section.split(';') if kw.strip()]
                
                if not divisions:
                    logger.warning("No divisions found in keywords section")
                if not keywords:
                    logger.warning("No keywords found in keywords section")
                logger.debug(f"Found {len(divisions)} divisions and {len(keywords)} keywords")

        # Extract previous years offered
        offerings = {}
        offerings_text = []
        offerings_header = soup.find('h4', string='Offerings')
        if not offerings_header:
            logger.warning("Offerings section not found, setting empty offerings")
        else:
            for element in find_next_siblings_with_text(offerings_header):
                if isinstance(element, Tag) and element.name == 'a':
                    text = element.text.strip()
                    if text:
                        link = element.get('href', '')
                        if "https" not in link:
                            link = "https://www.amherst.edu" + link
                        offerings[text] = link
                elif isinstance(element, str):
                    clean_text = element.replace('Other years:', '').replace('Offered in', '')

                    # Skip if the cleaned text contains only symbols
                    if not re.search(r'[a-zA-Z0-9]', clean_text):
                        continue

                    # Split by comma and clean each year
                    offerings_text = [year.strip() for year in clean_text.split(',') if year.strip()]

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
            "course_materials_links": materials_links,
            "description": description,
            "course_times_location": times_html,
            "keywords": keywords,
            "offerings": offerings
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
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def fetch_url_with_retry(url: str, session: requests.Session) -> Tuple[bool, str]:
    """Fetch URL content with retry logic"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
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
    with open(output_path, 'w') as f:
        json.dump(all_courses, f, indent=4)
    logger.info(f"Saved incremental results to {output_path}")

def parse_all_courses(testing_mode: bool = False):
    """Parse all course pages using parse_course_first_deg."""
    output_path = 'course_catelogue_scraper/parsing_results/parsed_courses_detailed.json'
    failed_urls = []
    
    try:
        # Load all department courses
        with open('course_catelogue_scraper/parsing_results/all_department_courses.json', 'r') as f:
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
                            logger.error(f"Error parsing course content for {url} on retry: {e}")

        save_incremental_results(output_path, all_courses)
        return all_courses

    except FileNotFoundError:
        logger.error("all_department_courses.json not found")
        return {}
    except Exception as e:
        logger.error(f"Error parsing courses: {e}")
        return {}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse Amherst College course catalog')
    parser.add_argument('--testing', action='store_true', help='Enable testing mode with incremental saves')
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set logging level (default: WARNING)'
    )
    args = parser.parse_args()
    
    # Set logging level from command line argument
    logger.setLevel(getattr(logging, args.log_level))
    
    parse_all_courses(testing_mode=args.testing)