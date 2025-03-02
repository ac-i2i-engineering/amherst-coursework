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
            'id': course.id,
            'name': course.courseName,
            'description': course.courseDescription,
            'departments': [{'code': d.code, 'name': d.name} for d in course.departments.all()],
            'courseCodes': [c.value for c in course.courseCodes.all()],
            'divisions': [d.name for d in course.divisions.all()],
            'keywords': [k.name for k in course.keywords.all()]
        }
        return JsonResponse({'course': course_data})
    except Course.DoesNotExist:
        return JsonResponse({'error': 'Course not found'}, status=404)
    


def compute_similarity_scores(query: str, information: List[str]) -> List[float]:
    """
    Compute cosine similarity scores between a query and a list of information.

    This function calculates the similarity between a given query string and 
    a list of information using the TF-IDF vectorization technique and cosine similarity.
    It assigns a score between 0 and 1 to each title, where higher values indicate 
    greater similarity.

    Parameters
    ----------
    query : str
        The input query string to compare against the list of information.
    information : list of str
        A list of event information to compare with the query.

    Returns
    -------
    list of float
        A list of similarity scores, where each score corresponds to the 
        similarity between the query and a title in `information`.

    Notes
    -----
    - The function removes English stop words before computing similarity.
    - If `query` or `information` is empty, the function returns a list of zeros.

    Examples
    --------
    >>> information = ["AI in Healthcare", "Machine Learning Workshop", "Deep Learning Seminar"]
    >>> compute_similarity_scores("Healthcare AI", information)
    [0.72, 0.15, 0.10]  # Example output, actual values may vary

    >>> compute_similarity_scores("", information)
    [0.0, 0.0, 0.0]
    """
    if not query or not information:
        return [0] * len(information)
    
    # Initialize TF-IDF vectorizer
    vectorizer = TfidfVectorizer(stop_words='english')
    
    # Combine query and information for vectorization
    all_texts = [query] + information
    
    # Create TF-IDF matrix
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    
    # Compute cosine similarity between query and each title
    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])
    
    return similarities[0]