from django.shortcuts import get_object_or_404, render
from .models import Course, Department


def home(request):
    departments = Department.objects.all().order_by("name")
    selected_dept = request.GET.get("department", "")

    courses = Course.objects.all().order_by("courseName")
    if selected_dept:
        courses = courses.filter(departments__code=selected_dept)

    return render(
        request,
        "amherst_coursework_algo/home.html",
        {
            "departments": departments,
            "courses": courses,
            "selected_dept": selected_dept,
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
