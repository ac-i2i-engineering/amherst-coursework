import requests
from bs4 import BeautifulSoup
import json
from typing import List, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Course types to exclude from the catalog
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

def get_catalog_links() -> List[Dict[str, str]]:
    # Base URL of the catalog
    base_url = "https://www.amherst.edu"
    catalog_url = f"{base_url}/academiclife/college-catalog/2425#tab_4"
    
    # Headers to mimic browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    }
    
    try:
        logger.info(f"Fetching catalog from {catalog_url}")
        response = requests.get(catalog_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the catalog section
        catalog_section = soup.find('div', id='tab_4')
        
        if not catalog_section:
            logger.error("Could not find catalog section (div#tab_4)")
            return []
            
        # Extract all department links
        departments = []
        links = catalog_section.find_all('a', class_='acad-cat-subcat')
        
        if not links:
            logger.error("No department links found")
            return []
            
        for link in links:
            dept_name = link.text.strip()
            if dept_name not in EXCLUDED_COURSE_TYPES:
                departments.append({
                    'name': dept_name,
                    'url': base_url + link['href']
                })
        
        # Save to JSON file
        with open('parsing_results/department_links.json', 'w') as f:
            json.dump(departments, f, indent=4)
        
        logger.info(f"Successfully extracted {len(departments)} departments")
        return departments
    
    except requests.RequestException as e:
        logger.error(f"Error fetching catalog: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return []

def get_department_courses(department_url: str) -> List[str]:
    """Parse a department page and extract Spring 2024 course links."""
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
        curriculum_body = soup.find('div', class_='course-curriculum-body')
        
        if not curriculum_body:
            logger.error(f"No curriculum body found for {department_url}")
            return []
        
        # Find all links containing "Spring 2024"
        spring_links = []
        for link in curriculum_body.find_all('a'):
            if "Spring 2024" in link.text:
                course_url = link['href']
                if not course_url.startswith('http'):
                    course_url = "https://www.amherst.edu" + course_url
                spring_links.append(course_url)
        
        logger.info(f"Found {len(spring_links)} Spring 2024 courses")
        return spring_links
        
    except requests.RequestException as e:
        logger.error(f"Error fetching department page: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error parsing department page: {e}")
        return []

def get_all_spring_courses():
    """Get Spring 2024 course links from all departments."""
    try:
        departments = get_catalog_links()
        all_courses = {}
        
        for dept in departments:
            dept_name = dept['name']
            dept_url = dept['url']
            courses = get_department_courses(dept_url)
            all_courses[dept_name] = courses
            
        # Save results
        with open('parsing_results/spring_2024_courses.json', 'w') as f:
            json.dump(all_courses, f, indent=4)
            
        return all_courses
            
    except Exception as e:
        logger.error(f"Error collecting all courses: {e}")
        return {}

def parse_course_page(course_url: str):
    """Parse individual course page and return structured data."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(course_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        course_div = soup.find('div', id='academics-course-list')
        if not course_div:
            logger.error(f"No course content found at {course_url}")
            return None
            
        # Extract basic info
        term = course_div.find('h2', class_='academics-course-list-term').text.strip()
        title = course_div.find('h3').text.strip()
        
        # Extract departments and course numbers
        listing_text = course_div.find('p').text
        departments = []
        course_numbers = []
        for part in listing_text.split(','):
            if 'as' in part:
                dept_num = part.split('as')[-1].strip()
                course_numbers.append(dept_num)
                departments.append(part.split('as')[0].strip())
        
        # Extract faculty
        faculty = []
        faculty_p = course_div.find('h4', text='Faculty').find_next('p')
        for prof in faculty_p.find_all('a'):
            faculty.append(prof.text.strip())
            
        # Extract description
        desc_paras = course_div.find('h4', text='Description').find_next_siblings('p')
        description = ' '.join(p.text.strip() for p in desc_paras)
        
        # Extract meeting times
        times = []
        location = ''
        details = course_div.find('details')
        if details:
            time_div = details.find('div', class_='details-wrapper')
            if time_div:
                for line in time_div.text.strip().split('\n'):
                    if any(day in line for day in ['Mo', 'Tu', 'We', 'Th', 'Fr']):
                        times.append(line.strip())
                    if any(building in line for building in ['FAYE', 'MERR', 'WEBS']):
                        location = line.strip()
        
        # Extract past offerings
        offerings = []
        offerings_section = course_div.find('h4', text='Offerings')
        if offerings_section:
            for link in offerings_section.find_next('b').find_next_siblings('a'):
                offerings.append(link.text.strip())
                
        return {
            'term': term,
            'title': title,
            'departments': departments,
            'course_numbers': course_numbers,
            'faculty': faculty,
            'description': description,
            'times': times,
            'location': location,
            'past_offerings': offerings
        }
            
    except Exception as e:
        logger.error(f"Error parsing course page {course_url}: {e}")
        return None
    
def parse_all_courses(courses: Dict[str, List[str]]):
    """Parse all course pages."""
    all_courses = {}
    for dept, course_urls in courses.items():
        all_courses[dept] = []
        for url in course_urls:
            course_data = parse_course_page(url)
            if course_data:
                all_courses[dept].append(course_data)
    
    # Save to JSON
    with open('parsing_results/parsed_courses.json', 'w') as f:
        json.dump(all_courses, f, indent=4)

    return all_courses

if __name__ == "__main__":
    departments = get_catalog_links()
    print(f"Found {len(departments)} departments")
    print("Links saved to department_links.json")
    courses = get_all_spring_courses()
    print(f"Saved Spring 2024 courses to spring_2024_courses.json")
    parsed_courses = parse_all_courses(courses)
    print