import re
import json
import os
from django.shortcuts import get_object_or_404, render
from .models import Course, Department, Division, CourseCode
from django.db.models import Q
from django.http import JsonResponse
from datetime import datetime, time, timedelta
import pytz
from amherst_coursework_algo.config.course_dictionaries import (
    DEPARTMENT_CODE_TO_NAME,
    DEPARTMENT_NAME_TO_CODE,
)
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import List


def home(request):
    courses = Course.objects.all()
    
    try:
        json_path = os.path.join(
            os.path.dirname(__file__),
            'static',
            'data',
            'parsed_courses_second_deg.json'
        )
        with open(json_path, 'r') as f:
            data = json.load(f)

        course_info_map = {}
        for dept_courses in data.values():
            for course_data in dept_courses:
                professors = set()
                time_slots = []
                if 'section_information' in course_data:
                    for section in course_data['section_information'].values():
                        if section.get('professor_name'):
                            # Add only the last name to the set
                            professors.add(get_last_name(section['professor_name']))
                        
                        # Collect all time slots
                        days = ['mon', 'tue', 'wed', 'thu', 'fri']
                        for day in days:
                            start = section.get(f'{day}_start_time')
                            end = section.get(f'{day}_end_time')
                            if start and end:
                                time_slots.append((day, start, end))
                
                course_info_map[course_data['course_name']] = {
                    'professor_name': ', '.join(professors) if professors else None,
                    'meeting_times': format_meeting_times(time_slots) if time_slots else None
                }

        # Add info to course objects
        for course in courses:
            if course.courseName in course_info_map:
                info = course_info_map[course.courseName]
                course.professor_name = info['professor_name']
                course.meeting_times = info['meeting_times']
            else:
                course.professor_name = None
                course.meeting_times = None

    except Exception as e:
        print(f"Error loading course data: {e}")
        for course in courses:
            course.professor_name = None
            course.meeting_times = None

    return render(request, "amherst_coursework_algo/home.html", {
        "courses": courses,
        "DEPARTMENT_CODE_TO_NAME": json.dumps(DEPARTMENT_CODE_TO_NAME),
    })


def get_cart_courses(request):
    course_ids = request.GET.getlist("ids[]")
    courses = Course.objects.filter(id__in=course_ids)
    
    # Load course schedule data from JSON
    try:
        json_path = os.path.join(
            os.path.dirname(__file__),
            'static',
            'data',
            'parsed_courses_second_deg.json'
        )
        with open(json_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading course data: {e}")
        return JsonResponse({"error": "Could not load course data"}, status=500)

    # Create a mapping of course names to their schedule data
    course_schedule_map = {}
    for dept_courses in data.values():
        for course_data in dept_courses:
            course_schedule_map[course_data['course_name']] = course_data

    # Build response data including schedules
    cart_data = []
    for course in courses:
        course_info = {
            "id": course.id,
            "name": course.courseName,
            "course_acronyms": [code.value for code in course.courseCodes.all()],
        }
        
        # Add schedule information if available
        if course.courseName in course_schedule_map:
            schedule_data = course_schedule_map[course.courseName]
            course_info.update({
                "section_information": schedule_data.get('section_information', {}),
                "course_acronyms": schedule_data.get('course_acronyms', [])
            })
        
        cart_data.append(course_info)

    return JsonResponse({"courses": cart_data})


def course_details(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Get course schedule data from JSON
    try:
        json_path = os.path.join(
            os.path.dirname(__file__),
            'static',
            'data',
            'parsed_courses_second_deg.json'
        )
        with open(json_path, 'r') as f:
            data = json.load(f)
            # Find the matching course in JSON data
            course_data = None
            for dept_courses in data.values():
                for c in dept_courses:
                    if c['course_name'] == course.courseName:
                        course_data = c
                        break
                if course_data:
                    break
    except Exception as e:
        print(f"Error loading course data: {e}")
        course_data = None

    return render(
        request,
        "amherst_coursework_algo/course_details_partial.html",
        {
            "course": course,
            "courses": [course_data] if course_data else [],
            "times": [f"{hour:02d}:00" for hour in range(8, 18)],
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
