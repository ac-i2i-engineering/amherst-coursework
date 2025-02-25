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
    courses = Course.objects.all().order_by("courseName")
    return render(
        request,
        "amherst_coursework_algo/home.html",
        {
            "courses": courses,
            "DEPARTMENT_CODE_TO_NAME": DEPARTMENT_CODE_TO_NAME,
        },
    )


def get_cart_courses(request):
    course_ids = request.GET.getlist("ids[]")
    courses = Course.objects.filter(id__in=course_ids)
    cart_data = [{"id": course.id, "name": course.courseName} for course in courses]
    return JsonResponse({"courses": cart_data})


def course_details(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    return render(
        request,
        "amherst_coursework_algo/course_details_partial.html",
        {"course": course},
    )
