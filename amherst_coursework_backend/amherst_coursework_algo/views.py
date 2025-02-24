import re
from django.shortcuts import get_object_or_404, render
from .models import Course, Department, Division, CourseCode
from django.db.models import Q
from django.http import JsonResponse
from amherst_coursework_algo.config.course_dictionaries import (
    DEPARTMENT_CODE_TO_NAME,
    DEPARTMENT_NAME_TO_CODE,
)


def home(request):
    departments = Department.objects.all().order_by("name")
    divisions = Division.objects.all().order_by("name")
    levels = ["100", "200", "300", "400"]
    search_query = request.GET.get("search", "")

    cleaned_code_query = re.sub(r"\W+", "", search_query).upper()
    cleaned_department_query = re.sub(r"[^\w\s]", "", search_query).strip()

    courses = Course.objects.all().order_by("courseName")

    if cleaned_code_query in DEPARTMENT_CODE_TO_NAME:
        department = Department.objects.get(
            name=DEPARTMENT_CODE_TO_NAME[cleaned_code_query]
        )
        courses = department.courses.all().distinct()
    elif any(
        dept.lower() == cleaned_department_query.lower()
        for dept in DEPARTMENT_NAME_TO_CODE
    ):
        # Find the actual department name with correct capitalization
        dept_name = next(
            dept
            for dept in DEPARTMENT_NAME_TO_CODE
            if dept.lower() == cleaned_department_query.lower()
        )
        department = Department.objects.get(name=dept_name)
        courses = department.courses.all().distinct()
    elif search_query:
        courses = courses.filter(courseName__icontains=search_query).distinct()

    return render(
        request,
        "amherst_coursework_algo/home.html",
        {
            "departments": departments,
            "divisions": divisions,
            "levels": levels,
            "courses": courses,
            "search_query": search_query,
        },
    )


def get_cart_courses(request):
    course_ids = request.GET.getlist("ids[]")
    courses = Course.objects.filter(id__in=course_ids)
    cart_data = [{"id": course.id, "name": course.courseName} for course in courses]
    return JsonResponse({"courses": cart_data})


def course_details(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    # Return partial template for AJAX requests
    return render(
        request,
        "amherst_coursework_algo/course_details_partial.html",
        {"course": course},
    )
