from django.shortcuts import get_object_or_404, render
from .models import Course, Department, Division, CourseCode


def home(request):
    departments = Department.objects.all().order_by("name")
    divisions = Division.objects.all().order_by("name")
    levels = ["100", "200", "300", "400"]
    selected_depts = request.GET.getlist("department", "")
    selected_div = request.GET.get("division", "")
    selected_level = request.GET.get("level", "")

    courses = Course.objects.all().order_by("courseName")
    if selected_depts:
        courses = courses.filter(departments__code__in=selected_depts)
    if selected_div:
        courses = courses.filter(divisions__name=selected_div)
    if selected_level:
        level_prefix = selected_level[0]

        courses = courses.filter(
            courseCodes__value__contains=f"-{level_prefix}"
        ).distinct()
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
            "selected_div": selected_div,
            "selected_level": selected_level,
        },
    )


def course_details(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        # Return partial template for AJAX requests
        return render(
            request,
            "amherst_coursework_algo/course_details_partial.html",
            {"course": course},
        )
    # Return full template for direct visits
    return render(
        request, "amherst_coursework_algo/course_details.html", {"course": course}
    )
