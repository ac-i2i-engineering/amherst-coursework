import re
import json
import os
from django.shortcuts import get_object_or_404, render
from .models import Course, Department, Division, CourseCode, Section
from django.db.models import Q
from django.http import JsonResponse
from datetime import datetime, time, timedelta
import pytz
from amherst_coursework_algo.config.course_dictionaries import (
    DEPARTMENT_CODE_TO_NAME,
    DEPARTMENT_NAME_TO_CODE,
)
from typing import List
from .masked_filters import filter
import logging
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# Get logger
logger = logging.getLogger(__name__)

PER_PAGE = 40  # Number of courses per page


def home(request):
    search = request.GET.get("search", "")
    search_query = search.lower()
    page = request.GET.get("page", 1)

    # Get initial courses
    all_courses = Course.objects.prefetch_related(
        "courseCodes", "sections__professor"
    ).all()

    if search_query:
        courses = filter(search_query, all_courses)
    else:
        # Sort by course name for default view (alphabetically)
        courses = sorted(all_courses, key=lambda c: c.courseName.lower())

    # Process courses with professor and meeting time info
    for course in courses:
        professors = set()
        time_slots = []

        for section in course.sections.all():
            if section.professor:
                professors.add(section.professor.name.split()[-1])

            days = [
                ("mon", section.monday_start_time, section.monday_end_time),
                ("tue", section.tuesday_start_time, section.tuesday_end_time),
                ("wed", section.wednesday_start_time, section.wednesday_end_time),
                ("thu", section.thursday_start_time, section.thursday_end_time),
                ("fri", section.friday_start_time, section.friday_end_time),
            ]

            for day_prefix, start_time, end_time in days:
                if start_time and end_time:
                    time_slots.append(
                        (
                            section.section_number,
                            day_prefix,
                            start_time.strftime("%I:%M %p"),
                            end_time.strftime("%I:%M %p"),
                        )
                    )

        course.professor_name = ", ".join(professors) if professors else None
        course.meeting_times = (
            format_meeting_times(time_slots, False) if time_slots else None
        )
        course.section_with_time = (
            format_meeting_times(time_slots, True) if time_slots else None
        )

    # Add pagination
    paginator = Paginator(list(courses), PER_PAGE)
    try:
        courses_page = paginator.page(page)
    except PageNotAnInteger:
        courses_page = paginator.page(1)
    except EmptyPage:
        courses_page = paginator.page(paginator.num_pages)

    context = {
        "courses": courses_page,
        "page_obj": courses_page,
        "DEPARTMENT_CODE_TO_NAME": json.dumps(DEPARTMENT_CODE_TO_NAME),
        "search_query": search,
        "total_pages": paginator.num_pages,
        "current_page": int(page),
    }

    return render(request, "amherst_coursework_algo/home.html", context)


def format_section_time(time_value):
    return time_value.strftime("%I:%M %p") if time_value else None


def format_meeting_times(time_slots, sections):
    # Group times by their start and end time and track section numbers
    time_groups = {}
    day_map = {"mon": "M", "tue": "T", "wed": "W", "thu": "Th", "fri": "F"}
    day_order = {"M": 0, "T": 1, "W": 2, "Th": 3, "F": 4}

    for section_num, day, start, end in time_slots:
        # Include section number in the key to distinguish different sections
        section_time_key = f"{section_num}-{start}-{end}"
        if section_time_key not in time_groups:
            time_groups[section_time_key] = {
                "days": set(),
                "section": section_num,
                "time": f"{start}-{end}",
            }
        time_groups[section_time_key]["days"].add(day_map[day])

    # Format each group
    formatted_times = []
    if sections:
        for key, info in time_groups.items():
            # Sort using custom day order
            days = "".join(sorted(list(info["days"]), key=lambda x: day_order[x]))
            start, end = info["time"].split("-")

            # Format the time properly
            try:
                start_time = datetime.strptime(start.strip(), "%I:%M %p")
                end_time = datetime.strptime(end.strip(), "%I:%M %p")
                formatted_start = start_time.strftime("%I:%M %p").lstrip("0")
                formatted_end = end_time.strftime("%I:%M %p").lstrip("0")
                formatted_times.append(
                    f"{info['section']}~{days} {formatted_start} - {formatted_end}"
                )
            except ValueError:
                formatted_times.append(
                    f"{info['section']}~{days} {start.strip()} - {end.strip()}"
                )
    else:
        # For non-section display (regular meeting times without section numbers)
        # Group by unique time + day combinations
        display_groups = {}
        for key, info in time_groups.items():
            time_key = info["time"]
            if time_key not in display_groups:
                display_groups[time_key] = {"days": set()}
            display_groups[time_key]["days"].update(info["days"])

        for time_range, info in display_groups.items():
            # Sort using custom day order
            days = "".join(sorted(list(info["days"]), key=lambda x: day_order[x]))
            start, end = time_range.split("-")

            # Format the time properly
            try:
                start_time = datetime.strptime(start.strip(), "%I:%M %p")
                end_time = datetime.strptime(end.strip(), "%I:%M %p")
                formatted_start = start_time.strftime("%I:%M %p").lstrip("0")
                formatted_end = end_time.strftime("%I:%M %p").lstrip("0")
                formatted_times.append(f"{days} {formatted_start} - {formatted_end}")
            except ValueError:
                formatted_times.append(f"{days} {start.strip()} - {end.strip()}")

    return " | ".join(formatted_times)


def get_cart_courses(request):
    cart_items = json.loads(request.GET.get("cart", "[]"))
    cart_data = []

    for item in cart_items:
        try:
            course_id = item.get("courseId")
            section_id = item.get("sectionId")

            course = Course.objects.prefetch_related(
                "courseCodes", "sections__professor"
            ).get(id=course_id)

            section = course.sections.get(section_number=section_id)

            course_info = {
                "id": course.id,
                "name": course.courseName,
                "credits": course.credits,
                "course_acronyms": [code.value for code in course.courseCodes.all()],
                "section_information": {
                    str(section.section_number): {
                        "section_number": str(section.section_number),
                        "professor_name": (
                            section.professor.name if section.professor else None
                        ),
                        "course_location": section.location,
                        "mon_start_time": format_section_time(
                            section.monday_start_time
                        ),
                        "mon_end_time": format_section_time(section.monday_end_time),
                        "tue_start_time": format_section_time(
                            section.tuesday_start_time
                        ),
                        "tue_end_time": format_section_time(section.tuesday_end_time),
                        "wed_start_time": format_section_time(
                            section.wednesday_start_time
                        ),
                        "wed_end_time": format_section_time(section.wednesday_end_time),
                        "thu_start_time": format_section_time(
                            section.thursday_start_time
                        ),
                        "thu_end_time": format_section_time(section.thursday_end_time),
                        "fri_start_time": format_section_time(
                            section.friday_start_time
                        ),
                        "fri_end_time": format_section_time(section.friday_end_time),
                    }
                },
            }
            cart_data.append(course_info)
        except Course.DoesNotExist:
            logger.error(f"ERROR: Course with ID {course_id} not found")
            continue
        except Section.DoesNotExist:
            logger.error(
                f"ERROR: Section with ID {section_id} not found for course {course_id}"
            )
            continue
        except Exception as e:
            logger.error(f"ERROR: Unexpected error processing item {item}: {str(e)}")
            continue

    return JsonResponse({"courses": cart_data})


def course_details(request, course_id):
    course = get_object_or_404(
        Course.objects.prefetch_related(
            "courseCodes",
            "sections__professor",
            "divisions",
            "departments",
            "keywords",
            "professors",
            "required_courses__courses__courseCodes",
            "recommended_courses__courseCodes",
            "corequisites__courseCodes",
            "placement_course__courseCodes",
            "fallOfferings",
            "springOfferings",
            "janOfferings",
        ),
        id=course_id,
    )

    return render(
        request,
        "amherst_coursework_algo/course_details_partial.html",
        {
            "course": course,
        },
    )


def get_course_by_id(request, course_id):
    try:
        course = Course.objects.get(id=course_id)
        course_data = {
            "id": course.id,
            "name": course.courseName,
            "description": course.courseDescription,
            "departments": [
                {"code": d.code, "name": d.name} for d in course.departments.all()
            ],
            "courseCodes": [c.value for c in course.courseCodes.all()],
            "divisions": [d.name for d in course.divisions.all()],
            "keywords": [k.name for k in course.keywords.all()],
        }
        return JsonResponse({"course": course_data})
    except Course.DoesNotExist:
        return JsonResponse({"error": "Course not found"}, status=404)


def get_course_sections(request, course_id):
    sections = Section.objects.filter(section_for_id=course_id).select_related(
        "professor"
    )
    sections_data = [
        {
            "section_number": str(section.section_number),
            "professor_name": section.professor.name,
            "location": section.location,
            "monday_start_time": format_section_time(section.monday_start_time),
            "monday_end_time": format_section_time(section.monday_end_time),
            "tuesday_start_time": format_section_time(section.tuesday_start_time),
            "tuesday_end_time": format_section_time(section.tuesday_end_time),
            "wednesday_start_time": format_section_time(section.wednesday_start_time),
            "wednesday_end_time": format_section_time(section.wednesday_end_time),
            "thursday_start_time": format_section_time(section.thursday_start_time),
            "thursday_end_time": format_section_time(section.thursday_end_time),
            "friday_start_time": format_section_time(section.friday_start_time),
            "friday_end_time": format_section_time(section.friday_end_time),
        }
        for section in sections
    ]
    return JsonResponse(sections_data, safe=False)


def about(request):
    return render(request, "amherst_coursework_algo/about.html")
