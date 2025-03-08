import re
from django.shortcuts import get_object_or_404, render
from .models import Course, Department, Division, CourseCode
from django.db.models import Q
from django.http import JsonResponse
from amherst_coursework_algo.config.course_dictionaries import (
    DEPARTMENT_CODE_TO_NAME,
    DEPARTMENT_NAME_TO_CODE,
)
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import List


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
