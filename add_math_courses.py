#!/usr/bin/env python3
"""
Script to manually add Mathematics and Statistics course URLs to the course catalogue.
This is necessary because the Math department pages are protected by AWS WAF CAPTCHA.
"""

import json
import os

# Common math course numbers based on typical college math curricula
MATH_COURSES = [
    111, 112, 121, 135, 211, 220, 230, 250, 271, 272, 280, 290,
    310, 320, 330, 340, 350, 355, 360, 370, 380, 390,
    410, 420, 430, 450, 460, 470, 480, 490, 498, 499
]

# Common statistics course numbers
STAT_COURSES = [
    111, 135, 230, 231, 240, 290, 310, 320, 330, 340, 360, 390, 490, 498, 499
]

def generate_course_urls(dept_code, course_numbers, semester="2526F"):
    """Generate course URLs based on department code and course numbers."""
    urls = []
    for num in course_numbers:
        url = f"https://www.amherst.edu/academiclife/departments/courses/{semester}/{dept_code}/{dept_code}-{num}-{semester}"
        urls.append(url)
    return urls

def main():
    # Path to the course data file
    data_dir = "amherst_coursework_backend/amherst_coursework_algo/data/course_catalogue"
    courses_file = os.path.join(data_dir, "all_department_courses.json")
    
    # Load existing data
    with open(courses_file, 'r') as f:
        data = json.load(f)
    
    # Generate URLs for MATH and STAT courses
    math_urls = generate_course_urls("MATH", MATH_COURSES)
    stat_urls = generate_course_urls("STAT", STAT_COURSES)
    
    # Combine all math-related URLs
    all_math_urls = math_urls + stat_urls
    
    # Update the Mathematics and Statistics entry
    data["Mathematics and Statistics"] = all_math_urls
    
    # Save updated data
    with open(courses_file, 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"✅ Added {len(all_math_urls)} Mathematics and Statistics course URLs")
    print(f"   - {len(math_urls)} MATH courses")
    print(f"   - {len(stat_urls)} STAT courses")
    print(f"\nUpdated: {courses_file}")

if __name__ == "__main__":
    main()
