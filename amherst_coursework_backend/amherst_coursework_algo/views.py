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


def format_meeting_times(time_slots):
    # Group times by their start and end time
    time_groups = {}
    day_map = {'mon': 'M', 'tue': 'T', 'wed': 'W', 'thu': 'Th', 'fri': 'F'}
    
    # Define custom day order (Tuesday before Thursday)
    day_order = {'M': 0, 'T': 1, 'W': 2, 'Th': 3, 'F': 4}
    
    for day, start, end in time_slots:
        time_key = f"{start}-{end}"
        if time_key not in time_groups:
            time_groups[time_key] = set()
        time_groups[time_key].add(day_map[day])
    
    # Format each group
    formatted_times = []
    for time_range, days in time_groups.items():
        # Sort using custom day order
        days = ''.join(sorted(list(days), key=lambda x: day_order[x]))
        start, end = time_range.split('-')
        
        # Format the time properly
        try:
            start_time = datetime.strptime(start.strip(), '%I:%M %p')
            end_time = datetime.strptime(end.strip(), '%I:%M %p')
            formatted_start = start_time.strftime('%I:%M %p').lstrip('0')
            formatted_end = end_time.strftime('%I:%M %p').lstrip('0')
            formatted_times.append(f"{days} {formatted_start} - {formatted_end}")
        except ValueError:
            formatted_times.append(f"{days} {start.strip()} - {end.strip()}")
    
    return ' | '.join(formatted_times)

def get_last_name(full_name):
    """Extract last name from a full name"""
    return full_name.split()[-1] if full_name else None

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

def calendar_view(request):
    """View for displaying the course calendar"""
    # Generate times from 8:00 AM to 5:00 PM
    times = [datetime.strptime(f"{hour}:00", "%H:%M").time() for hour in range(8, 18)]
    
    # Get course data from JSON
    courses = []
    with open('amherst_coursework_algo/static/data/parsed_courses_second_deg.json') as f:
        data = json.load(f)
        for department_courses in data.values():
            courses.extend(department_courses)
    
    # Create events by day dictionary
    events_by_day = {
        'Monday': [],
        'Tuesday': [],
        'Wednesday': [],
        'Thursday': [],
        'Friday': []
    }
    
    # Process each course and its sections
    for course in courses:
        for section_id, section in course['section_information'].items():
            # Process each day's schedule
            day_times = [
                ('Monday', section.get('mon_start_time'), section.get('mon_end_time')),
                ('Tuesday', section.get('tue_start_time'), section.get('tue_end_time')),
                ('Wednesday', section.get('wed_start_time'), section.get('wed_end_time')),
                ('Thursday', section.get('thu_start_time'), section.get('thu_end_time')),
                ('Friday', section.get('fri_start_time'), section.get('fri_end_time'))
            ]
            
            for day_name, start_time_str, end_time_str in day_times:
                if start_time_str and end_time_str:
                    # Convert time strings to datetime.time objects
                    start_time = datetime.strptime(start_time_str, "%I:%M %p").time()
                    end_time = datetime.strptime(end_time_str, "%I:%M %p").time()
                    
                    # Calculate position and height for the event
                    top = (start_time.hour - 8) * 60 + (start_time.minute)  # Minutes from 8 AM
                    height = ((end_time.hour - start_time.hour) * 60 + 
                             (end_time.minute - start_time.minute))  # Duration in minutes
                    
                    event = {
                        "title": course['course_name'],
                        "location": section.get('course_location', 'TBA'),
                        "start_time": start_time,
                        "end_time": end_time,
                        "top": top,
                        "height": max(height, 30),  # Minimum height of 30 minutes
                        "column": 0,
                        "columns": 1,
                        "course_codes": course.get('course_acronyms', [])
                    }
                    events_by_day[day_name].append(event)
    
    # Sort events and handle overlaps for each day
    for day, events in events_by_day.items():
        if events:
            events.sort(key=lambda x: x['start_time'])
            
            # Handle overlapping events
            current_group = []
            max_columns = 1
            
            for event in events:
                # Keep only events that overlap with current event
                current_group = [e for e in current_group if (
                    e['start_time'] < event['end_time'] and 
                    event['start_time'] < e['end_time']
                )]
                
                current_group.append(event)
                
                # Assign columns for current group
                used_columns = set()
                for e in current_group:
                    column = 0
                    while column in used_columns:
                        column += 1
                    e['column'] = column
                    used_columns.add(column)
                
                max_columns = max(max_columns, len(current_group))
            
            # Update column count for all events in the day
            for event in events:
                event['columns'] = max_columns
