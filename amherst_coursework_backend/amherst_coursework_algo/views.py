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
from . import ai_advisor

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


def ai_course_advisor(request):
    """
    AI-powered course advisor endpoint
    Analyzes student's schedule and provides personalized recommendations
    """
    try:
        # Get cart items from request
        cart_json = request.GET.get('cart', '[]')
        cart_items = json.loads(cart_json)
        user_question = request.GET.get('question', '')
        
        # Fetch full course data for cart items
        cart_courses = []
        for item in cart_items:
            try:
                course_id = item.get('courseId')
                course = Course.objects.prefetch_related(
                    'courseCodes', 
                    'departments', 
                    'keywords',
                    'professors',
                    'required_courses__courses',
                    'recommended_courses'
                ).get(id=course_id)
                cart_courses.append(course)
            except Course.DoesNotExist:
                logger.warning(f"Course {course_id} not found in cart")
                continue
            except Exception as e:
                logger.error(f"Error fetching course {course_id}: {e}")
                continue
        
        # Build context for AI
        context = ai_advisor.build_course_context(cart_courses)
        
        # Search for relevant courses based on student's interests
        # Build search queries from their current schedule
        search_queries = []
        
        # Add department-based searches
        for dept in context['departments_covered'][:3]:  # Top 3 departments
            search_queries.append(dept)
        
        # Add keyword-based searches
        for keyword in context['common_keywords'][:3]:  # Top 3 keywords
            search_queries.append(keyword)
        
        # Add general complementary searches based on what they're taking
        if 'Anthropology' in context['departments_covered']:
            search_queries.extend(['sociology', 'cultural studies', 'history'])
        if 'Computer Science' in context['departments_covered']:
            search_queries.extend(['mathematics', 'statistics', 'data science'])
        if 'Biology' in context['departments_covered']:
            search_queries.extend(['chemistry', 'environmental science', 'statistics'])
        
        # If asking for suggestions, add more general searches
        if 'suggest' in user_question.lower() or 'recommend' in user_question.lower():
            search_queries.extend(['quantitative reasoning', 'writing', 'humanities'])
        
        # Perform searches and collect relevant courses
        all_courses = Course.objects.prefetch_related('courseCodes', 'departments', 'keywords').all()
        relevant_courses = []
        seen_course_ids = set()
        
        for query in search_queries[:5]:  # Limit to 5 searches
            search_results = ai_advisor.search_courses(query, all_courses)
            for course in search_results[:10]:  # Top 10 from each search
                if course.id not in seen_course_ids:
                    relevant_courses.append(course)
                    seen_course_ids.add(course.id)
                if len(relevant_courses) >= 50:  # Max 50 courses in context
                    break
            if len(relevant_courses) >= 50:
                break
        
        # Add relevant courses to context
        context['available_courses_sample'] = [
            {
                'name': c.courseName,
                'codes': [code.value for code in c.courseCodes.all()],
                'description': c.courseDescription[:200] if c.courseDescription else '',
                'credits': c.credits,
                'departments': [d.name for d in c.departments.all()],
            }
            for c in relevant_courses
        ]
        
        # Generate AI response with search results
        advice_text = ai_advisor.generate_advisor_response(context, user_question)
        
        # Parse recommendations from response
        all_courses = Course.objects.prefetch_related('courseCodes', 'departments').all()
        recommendations = ai_advisor.parse_recommendations_from_response(
            advice_text, 
            all_courses
        )
        
        # Get IDs of courses already in cart to filter them out
        cart_course_ids = set(c.id for c in cart_courses)
        
        # Format recommendations for JSON response, excluding courses already in cart
        formatted_recommendations = []
        for rec in recommendations:
            course = rec['course']
            # Skip if course is already in the student's schedule
            if course.id in cart_course_ids:
                continue
                
            formatted_recommendations.append({
                'id': course.id,
                'name': course.courseName,
                'code': course.courseCodes.first().value if course.courseCodes.exists() else '',
                'credits': course.credits,
                'reason': rec['reason'],
                'departments': [d.name for d in course.departments.all()],
            })
        
        return JsonResponse({
            'success': True,
            'advice': advice_text,
            'recommendations': formatted_recommendations,
            'schedule_summary': {
                'total_credits': context['total_credits'],
                'num_courses': context['num_courses'],
                'departments': context['departments_covered'],
            }
        })
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in cart parameter: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Invalid cart data format'
        }, status=400)
    
    except Exception as e:
        logger.error(f"Error in AI advisor: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Failed to generate advice: {str(e)}'
        }, status=500)
