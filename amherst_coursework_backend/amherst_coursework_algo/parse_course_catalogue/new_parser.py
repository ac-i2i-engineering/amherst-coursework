import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

SCRIPT_DIR = Path(__file__).parent

HTML_FILE = SCRIPT_DIR / "workday_course_catalogue.html"
OUTPUT_FILE = SCRIPT_DIR / "new_course_parsed.json"

DAY_MAP = {
    "Monday": "mon",
    "Tuesday": "tue",
    "Wednesday": "wed",
    "Thursday": "thu",
    "Friday": "fri",
    "Saturday": "sat",
    "Sunday": "sun",
}

DEPARTMENT_CODE_TO_NAME = {
    "AMST": "American Studies",
    "ANTH": "Anthropology and Sociology",
    "SOCI": "Anthropology and Sociology",
    "ARCH": "Architectural Studies",
    "ARHA": "Art and the History of Art",
    "AAPI": "Asian American and Pacific Islander Studies",
    "ASLC": "Asian Languages and Civilizations",
    "BCBP": "Biochemistry and Biophysics",
    "BIOL": "Biology",
    "BLST": "Black Studies",
    "CHEM": "Chemistry",
    "CLAS": "Classics",
    "COLL": "Colloquia",
    "COSC": "Computer Science",
    "CRWR": "Creative Writing",
    "ECON": "Economics",
    "EDST": "Educational Studies",
    "ENGL": "English",
    "ENST": "Environmental Studies",
    "EUST": "European Studies",
    "FAMS": "Film and Media Studies",
    "FYSE": "First Year Seminar",
    "FREN": "French",
    "GEOL": "Geology",
    "GERM": "German",
    "HIST": "History",
    "LLAS": "Latinx and Latin American Studies",
    "LJST": "Law, Jurisprudence, and Social Thought",
    "MATH": "Mathematics",
    "STAT": "Statistics",
    "MLLN": "Mellon Seminar",
    "MUSI": "Music",
    "NEUR": "Neuroscience",
    "PHIL": "Philosophy",
    "PHYS": "Physics and Astronomy",
    "ASTR": "Physics and Astronomy",
    "POSC": "Political Science",
    "PSYC": "Psychology",
    "RELI": "Religion",
    "RUSS": "Russian",
    "SWAG": "Sexuality, Women's and Gender Studies",
    "SPAN": "Spanish",
    "THDA": "Theater and Dance",
}

DEPARTMENT_CODE_TO_DIVISION = {
    "AMST": "Humanities",
    "ANTH": "Social Sciences",
    "SOCI": "Social Sciences",
    "ARCH": "Humanities",
    "ARHA": "Humanities",
    "AAPI": "Humanities",
    "ASLC": "Humanities",
    "BCBP": "Natural Sciences",
    "BIOL": "Natural Sciences",
    "BLST": "Humanities",
    "CHEM": "Natural Sciences",
    "CLAS": "Humanities",
    "COLL": None,
    "COSC": "Natural Sciences",
    "CRWR": "Humanities",
    "ECON": "Social Sciences",
    "EDST": "Social Sciences",
    "ENGL": "Humanities",
    "ENST": "Natural Sciences",
    "EUST": "Humanities",
    "FAMS": "Humanities",
    "FYSE": None,
    "FREN": "Humanities",
    "GEOL": "Natural Sciences",
    "GERM": "Humanities",
    "HIST": "Humanities",
    "LLAS": "Humanities",
    "LJST": "Social Sciences",
    "MATH": "Natural Sciences",
    "STAT": "Natural Sciences",
    "MLLN": None,
    "MUSI": "Humanities",
    "NEUR": "Natural Sciences",
    "PHIL": "Humanities",
    "PHYS": "Natural Sciences",
    "ASTR": "Natural Sciences",
    "POSC": "Social Sciences",
    "PSYC": "Social Sciences",
    "RELI": "Humanities",
    "RUSS": "Humanities",
    "SWAG": "Humanities",
    "SPAN": "Humanities",
    "THDA": "Humanities",
}

SEMESTER_CODE = "2526S"

COURSE_CODE_RE = re.compile(r'\b([A-Z]{2,5})\s+(\d{3}[A-Z]?)\b')
OFFERED_AS_RE = re.compile(
    r'Offered as\s+([A-Z]{2,5}\s+\d{3}[A-Z]?(?:\s+and\s+[A-Z]{2,5}\s+\d{3}[A-Z]?)+)',
    re.IGNORECASE
)
SLASH_LISTING_RE = re.compile(
    r'\b([A-Z]{2,5}\s+\d{3}[A-Z]?(?:/[A-Z]{2,5}\s+\d{3}[A-Z]?)+)\b'
)


def dept_name_to_url_slug(dept_name):
    return dept_name.lower().replace(" ", "_").replace(",", "").replace("'", "")


def get_department_url(dept_name):
    slug = dept_name_to_url_slug(dept_name)
    return f"https://www.amherst.edu/academiclife/departments/{slug}/courses/{SEMESTER_CODE}"


def extract_cross_listings(primary_code, description):
    primary_fmt = primary_code.replace(" ", "-")
    acronyms = {primary_fmt}

    for m in OFFERED_AS_RE.finditer(description):
        for code_m in COURSE_CODE_RE.finditer(m.group(0)):
            acronyms.add(f"{code_m.group(1)}-{code_m.group(2)}")

    for m in SLASH_LISTING_RE.finditer(description):
        parts = m.group(0).split("/")
        for part in parts:
            cm = COURSE_CODE_RE.match(part.strip())
            if cm:
                acronyms.add(f"{cm.group(1)}-{cm.group(2)}")

    return sorted(acronyms)


def build_dept_metadata(acronyms):
    departments = {}

    for acr in acronyms:
        code = acr.split("-")[0]
        dept_name = DEPARTMENT_CODE_TO_NAME.get(code)
        if dept_name:
            if dept_name not in departments:
                departments[dept_name] = get_department_url(dept_name)

    return departments


def empty_time_block():
    return {
        f"{d}_{t}": None for d in DAY_MAP.values() for t in ["start_time", "end_time"]
    }


def parse_days_and_times(days_str, time_str):
    data = empty_time_block()
    start, end = [t.strip() for t in time_str.split("-")]

    for day in days_str.split("/"):
        day = day.strip()
        if day in DAY_MAP:
            key = DAY_MAP[day]
            data[f"{key}_start_time"] = start
            data[f"{key}_end_time"] = end
    return data


with open(HTML_FILE, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

courses = {}

course_items = soup.find_all("li", {"data-automation-id": "compositeContainer"})

for item_index, item in enumerate(course_items):
    try:
        header = item.find("div", {"data-automation-id": "promptOption"})
        if not header:
            continue

        header_text = header.get_text(strip=True)

        if " -" not in header_text:
            continue

        parts = header_text.split(" -", 1)
        left = parts[0]
        title = parts[1].lstrip() if len(parts) > 1 else ""

        if not title or "-" not in left:
            continue

        course_code, section_id = left.rsplit("-", 1)

        course_code = course_code.strip()
        section_id = section_id.strip()

        professor_name = None
        instructor_label = item.find("label", string="Instructors")
        if instructor_label:
            name_div = instructor_label.find_next("div", class_="gwt-Label")
            if name_div:
                professor_name = name_div.get_text(strip=True)

        location = None
        time_data = empty_time_block()

        meeting_divs = item.find_all("div", attrs={"aria-label": re.compile(r"\|")})
        for div in meeting_divs:
            text = div.get("aria-label", "")
            parts = [p.strip() for p in text.split("|")]
            if len(parts) == 3:
                location, days, times = parts
                parsed_times = parse_days_and_times(days, times)
                time_data.update(parsed_times)

        section_type = "Lecture"
        format_label = item.find("label", string="Instructional Format")
        if format_label:
            fmt = format_label.find_next("div", class_="gwt-Label")
            if fmt:
                section_type = fmt.get_text(strip=True)

        if section_type.lower() == "lab":
            section_key = f"{section_id}L"
        elif section_type.lower() == "discussion":
            section_key = f"{section_id}D"
        else:
            section_key = section_id

        tags = []
        tag_label = item.find("label", string="Course Tags")
        if tag_label:
            tag_ul = tag_label.find_next("ul")
            if tag_ul:
                tag_divs = tag_ul.find_all("div", class_="gwt-Label")
                tags = [t.get_text(strip=True) for t in tag_divs]

        desc_label = item.find("label", string="Course Section Description")
        description = None
        if desc_label:
            desc_div = desc_label.find_next("div")
        if desc_div:
            description = desc_div.get_text(strip=True)

        course_acronyms = extract_cross_listings(course_code, description)
        departments = build_dept_metadata(course_acronyms)

        if course_code not in courses:
            courses[course_code] = {
                "course_title": title,
                "course_description": description,
                "course_tags": tags,
                "course_acronyms": course_acronyms,
                "departments": departments,
                "section_information": {},
            }

        courses[course_code]["section_information"][section_key] = {
            "section_type": section_type,
            "professor_name": professor_name,
            "professor_link": None,
            "course_location": location,
            "course_materials_links": None,
            **time_data,
        }

    except Exception:
        continue

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(courses, f, indent=4)

print(f"Saved parsed data to {str(OUTPUT_FILE)}")