from django.shortcuts import get_object_or_404, render
from .models import Course


def home(request):
    courses = Course.objects.all().order_by("courseName")
    context = {
        "courses": courses,
    }
    return render(request, "amherst_coursework_algo/home.html", context)


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
