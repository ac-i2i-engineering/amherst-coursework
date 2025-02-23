from django.shortcuts import get_object_or_404, render
from .models import Course, Department, Division, CourseCode
from django.db.models import Q
from django.http import JsonResponse


def home(request):
    departments = Department.objects.all().order_by("name")
    divisions = Division.objects.all().order_by("name")
    levels = ["100", "200", "300", "400"]
    selected_depts = request.GET.getlist("department", "")
    selected_divs = request.GET.getlist("division", "")
    selected_levels = request.GET.getlist("level", "")
    search_query = request.GET.get("search", "")

    courses = Course.objects.all().order_by("courseName")
    if search_query:
        courses = courses.filter(courseName__icontains=search_query).distinct()
    if selected_depts:
        courses = courses.filter(departments__code__in=selected_depts).distinct()
    if selected_divs:
        courses = courses.filter(divisions__name__in=selected_divs).distinct()
    if selected_levels:
        level_prefixes = [selected_level[0] for selected_level in selected_levels]
        level_filters = Q()
        for prefix in level_prefixes:
            level_filters |= Q(courseCodes__value__contains=f"-{prefix}")
        courses = courses.filter(level_filters).distinct()
        print(f"Filtered courses: {[c.courseName for c in courses]}")

    return render(
        request,
        "amherst_coursework_algo/home.html",
        {
            "departments": departments,
            "divisions": divisions,
            "levels": levels,
            "courses": courses,
            "selected_depts": selected_depts,
            "selected_divs": selected_divs,
            "selected_levels": selected_levels,
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
