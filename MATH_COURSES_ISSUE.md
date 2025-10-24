# Mathematics and Statistics Courses Issue

## Problem
The Mathematics and Statistics department courses are missing from the database because the Amherst College website has implemented AWS WAF (Web Application Firewall) protection with CAPTCHA specifically for the Mathematics department pages.

## Evidence
All attempts to access Math department URLs result in a CAPTCHA challenge:
- `https://www.amherst.edu/academiclife/departments/mathematics-statistics/courses/2526F`
- `https://www.amherst.edu/academiclife/departments/courses/2526F/MATH/MATH-111-2526F`
- Any other Math-related course URLs

## Current State
- `all_department_courses.json`: `"Mathematics and Statistics": []`
- `parsed_courses_second_deg.json`: `"Mathematics and Statistics": []` (0 courses)
- All other 35 departments have courses successfully loaded

## Why This Matters
Users searching for "math", "mathematics", "statistics", "calculus", "algebra", etc. cannot find actual mathematics courses because they don't exist in the database.

## Solutions

### Option 1: Manual Data Entry (Recommended for immediate fix)
Someone with browser access needs to:
1. Visit https://www.amherst.edu/academiclife/departments/mathematics-statistics/courses/2526F
2. Solve the CAPTCHA
3. Manually copy the course list
4. Create a JSON file with the course data
5. Import it into the database

### Option 2: Browser Automation with CAPTCHA Solving
- Use Selenium/Playwright with a real browser
- Manually solve CAPTCHA once
- Save cookies/session
- Use saved session for subsequent requests
- **Note**: This may violate the website's terms of service

### Option 3: Contact Amherst IT
- Request API access or exemption from CAPTCHA for educational purposes
- Explain the use case (course search tool for students)
- Request a data export or alternative access method

### Option 4: Use Alternative Data Sources
- Check if Amherst provides course data through:
  - Course catalog PDFs
  - Academic API
  - Data exports for students
  - Banner/SIS system exports

## Temporary Workaround
The search algorithm has been optimized to:
1. Show mathematically-relevant courses from other departments (Physics, Economics, Computer Science)
2. Boost courses in the "Science & Mathematics" division
3. Prioritize courses with mathematical content in descriptions

This provides some value to users searching for math-related content, but is not a complete solution.

## Action Required
**Someone with browser access needs to manually fetch the Mathematics and Statistics course data.**

The parsing infrastructure is ready - we just need the raw HTML or course list from the Math department pages.
