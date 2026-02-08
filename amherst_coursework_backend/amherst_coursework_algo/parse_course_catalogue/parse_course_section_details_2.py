import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent

HTML_FILE = SCRIPT_DIR / "workday_course_catalogue.html"
OUTPUT_FILE = SCRIPT_DIR / "course_parsed.json"

DAY_MAP = {
    "Monday": "mon",
    "Tuesday": "tue",
    "Wednesday": "wed",
    "Thursday": "thu",
    "Friday": "fri",
    "Saturday": "sat",
    "Sunday": "sun",
}


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
        # -------------------------------
        # Course header
        # -------------------------------
        header = item.find("div", {"data-automation-id": "promptOption"})
        if not header:
            continue

        header_text = header.get_text(strip=True)
        # Example: AAPI 208-01 - A/P/A Sports
        # Handle cases where there might be missing space after dash: "AAPI 208-01 -A/P/A"
        if " -" not in header_text:
            print(
                f"Warning: Item {item_index} has malformed header: '{header_text}'. Skipping."
            )
            continue

        # Split on " -" and handle both " - " and " -" patterns
        parts = header_text.split(" -", 1)
        left = parts[0]
        title = parts[1].lstrip() if len(parts) > 1 else ""

        if not title:
            print(
                f"Warning: Item {item_index} has empty title: '{header_text}'. Skipping."
            )
            continue

        if "-" not in left:
            print(
                f"Warning: Item {item_index} has malformed course code: '{left}'. Skipping."
            )
            continue

        course_code, section_id = left.rsplit("-", 1)

        course_code = course_code.strip()
        section_id = section_id.strip()

        # -------------------------------
        # Instructor
        # -------------------------------
        professor_name = None
        instructor_label = item.find("label", string="Instructors")
        if instructor_label:
            name_div = instructor_label.find_next("div", class_="gwt-Label")
            if name_div:
                professor_name = name_div.get_text(strip=True)

        # -------------------------------
        # Section meeting blocks
        # -------------------------------
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

        # -------------------------------
        # Section type detection
        # -------------------------------
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

        # -------------------------------
        # Course tags (course-level)
        # -------------------------------
        tags = []
        tag_label = item.find("label", string="Course Tags")
        if tag_label:
            tag_ul = tag_label.find_next("ul")
            if tag_ul:
                tag_divs = tag_ul.find_all("div", class_="gwt-Label")
                tags = [t.get_text(strip=True) for t in tag_divs]

        # -------------------------------
        # Initialize course container
        # -------------------------------
        if course_code not in courses:
            courses[course_code] = {
                "course_title": title,
                "course_tags": tags,
                "section_information": {},
            }

        # -------------------------------
        # Store section
        # -------------------------------
        courses[course_code]["section_information"][section_key] = {
            "section_type": section_type,
            "professor_name": professor_name,
            "professor_link": None,
            "course_location": location,
            "course_materials_links": None,
            **time_data,
        }

    except Exception as e:
        print(f"Error processing item {item_index}: {e}")
        continue

# -------------------------------
# Write JSON
# -------------------------------
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(courses, f, indent=4)

print(f"Saved parsed data to {str(OUTPUT_FILE)}")
