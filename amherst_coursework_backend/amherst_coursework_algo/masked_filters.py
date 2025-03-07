from .models import Course
from django.http import JsonResponse, Http404
from amherst_coursework_algo.config.course_dictionaries import (
    DEPARTMENT_CODE_TO_NAME,
    DEPARTMENT_NAME_TO_CODE,
)
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import List
import json
from concurrent.futures import ThreadPoolExecutor


def normalize_code(code: str) -> str:
    """
    Remove any non-alphanumeric characters from the given code.

    Parameters
    ----------
    code : str
        The input code string to be normalized.

    Returns
    -------
    str
        The normalized code string containing only alphanumeric characters.
    """
    return "".join(c for c in code if c.isalnum())


def relevant_course_name(search_query: str, courses: list) -> list:
    """
    Return binary indicators for courses whose names contain the search query.

    Parameters
    ----------
    search_query : str
        The search query string to match against course names.
    courses : list
        A list of Course objects to be filtered.

    Returns
    -------
    list
        A list of binary indicators (1 or 0) indicating whether each course name contains the search query.
    """
    search_query = search_query.lower()
    return [1 if search_query in course.courseName.lower() else 0 for course in courses]


def relevant_department_codes(search_query: str, courses: list) -> list:
    """
    Return binary indicators for courses with matching department codes.

    Parameters
    ----------
    search_query : str
        The search query string to match against department codes.
    courses : list
        A list of Course objects to be filtered.

    Returns
    -------
    list
        A list of binary indicators (1 or 0) indicating whether each course has a matching department code.
    """
    search_query = search_query.lower()
    return [
        (
            1
            if any(
                search_query in dept.code.lower() for dept in course.departments.all()
            )
            else 0
        )
        for course in courses
    ]


def relevant_department_names(search_query: str, courses: list) -> list:
    """
    Return binary indicators for courses with matching department names.

    Parameters
    ----------
    search_query : str
        The search query string to match against department names.
    courses : list
        A list of Course objects to be filtered.

    Returns
    -------
    list
        A list of binary indicators (1 or 0) indicating whether each course has a matching department name.
    """
    search_query = search_query.lower()
    return [
        (
            1
            if any(
                search_query in dept.name.lower() for dept in course.departments.all()
            )
            else 0
        )
        for course in courses
    ]


def relevant_course_codes(search_query: str, courses: list) -> list:
    """
    Return binary indicators for courses with matching course codes.

    Parameters
    ----------
    search_query : str
        The search query string to match against course codes.
    courses : list
        A list of Course objects to be filtered.

    Returns
    -------
    list
        A list of binary indicators (1 or 0) indicating whether each course has a matching course code.
    """
    search_query = search_query.lower()
    return [
        (
            1
            if any(
                search_query in code.value.lower()
                or search_query in normalize_code(code.value.lower())
                for code in course.courseCodes.all()
            )
            else 0
        )
        for course in courses
    ]


def relevant_divisions(search_query: str, courses: list) -> list:
    """
    Return binary indicators for courses with matching divisions.

    Parameters
    ----------
    search_query : str
        The search query string to match against division names.
    courses : list
        A list of Course objects to be filtered.

    Returns
    -------
    list
        A list of binary indicators (1 or 0) indicating whether each course has a matching division.
    """
    search_query = search_query.lower()
    return [
        (
            1
            if any(
                search_query in division.name.lower()
                for division in course.divisions.all()
            )
            else 0
        )
        for course in courses
    ]


def relevant_keywords(search_query: str, courses: list) -> list:
    """
    Return binary indicators for courses with matching keywords.

    Parameters
    ----------
    search_query : str
        The search query string to match against keywords.
    courses : list
        A list of Course objects to be filtered.

    Returns
    -------
    list
        A list of binary indicators (1 or 0) indicating whether each course has a matching keyword.
    """
    search_query = search_query.lower()
    return [
        (
            1
            if any(
                search_query in keyword.name.lower()
                for keyword in course.keywords.all()
            )
            else 0
        )
        for course in courses
    ]


def relevant_descriptions(search_query: str, courses: list) -> list:
    """
    Return binary indicators for courses with matching descriptions.

    Parameters
    ----------
    search_query : str
        The search query string to match against course descriptions.
    courses : list
        A list of Course objects to be filtered.

    Returns
    -------
    list
        A list of binary indicators (1 or 0) indicating whether each course description contains the search query.
    """
    search_query = search_query.lower()
    return [
        1 if search_query in course.courseDescription.lower() else 0
        for course in courses
    ]


def relevant_professor_names(search_query: str, courses: list) -> list:
    """
    Return binary indicators for courses with matching professor names.

    Parameters
    ----------
    search_query : str
        The search query string to match against professor names.
    courses : list
        A list of Course objects to be filtered.

    Returns
    -------
    list
        A list of binary indicators (1 or 0) indicating whether each course has a matching professor.
    """
    search_query = search_query.lower()
    return [
        (
            1
            if any(
                search_query in professor.name.lower()
                for professor in course.professors.all()
            )
            else 0
        )
        for course in courses
    ]


def half_courses(search_query: str, courses: list) -> list:
    """
    Return binary indicators for half courses if query contains 'half'.

    Parameters
    ----------
    search_query : str
        The search query string to check for the word 'half'.
    courses : list
        A list of Course objects to be filtered.

    Returns
    -------
    list
        A list of binary indicators (1 or 0) indicating whether each course is a half course.
    """
    if "half" in search_query.lower():
        return [
            1 if len(str(course.id)) >= 4 and str(course.id)[-4] == "1" else 0
            for course in courses
        ]
    return [1] * len(courses)


def similarity_filtering(
    query: str, courses: list, similarity_threshold: float
) -> list:
    """
    Return binary indicators based on text similarity scores.

    Parameters
    ----------
    query : str
        The search query string to compare against course texts.
    courses : list
        A list of Course objects to be filtered.
    similarity_threshold : float
        The threshold above which a course is considered similar.

    Returns
    -------
    list
        A list of binary indicators (1 or 0) indicating whether each course text is similar to the query.
    """
    return [
        1 if query_course_similarity(query, course) > similarity_threshold else 0
        for course in courses
    ]


def query_course_similarity(query: str, course) -> float:
    """
    Compute similarity between query and course text.

    Parameters
    ----------
    query : str
        The search query string.
    course : Course
        The Course object whose text is to be compared.

    Returns
    -------
    float
        The similarity score between the query and the course text.
    """
    course_text = " ".join(
        [
            course.courseName or "",
            course.courseDescription or "",
            " ".join(dept.name for dept in course.departments.all()),
            " ".join(prof.name for prof in course.professors.all()),
            " ".join(keyword.name for keyword in course.keywords.all()),
        ]
    ).lower()

    # Use existing compute_similarity_scores function
    return compute_similarity_scores(query, [course_text])[0]


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
    vectorizer = TfidfVectorizer(stop_words="english")

    # Combine query and information for vectorization
    all_texts = [query] + information

    # Create TF-IDF matrix
    tfidf_matrix = vectorizer.fit_transform(all_texts)

    # Compute cosine similarity between query and each title
    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])

    return similarities[0]


def filter(request):

    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests allowed"}, status=405)

    try:
        # Parse request data
        data = json.loads(request.body)
        search_query = data.get("search_query", "").lower()
        course_ids = data.get("course_ids", [])
        similarity_threshold = data.get("similarity_threshold", 0.05)

        if not search_query:
            return JsonResponse({
                "status": "success", 
                "indicators": [1] * len(course_ids)
            })

        # Better error handling for course fetching
        courses = []
        for course_id in course_ids:
            try:
                course = Course.objects.get(id=course_id)
                courses.append(course)
            except Course.DoesNotExist:
                print("Error:" + str(course_id))
                # Skip non-existent courses
                continue

        if not courses:
            return JsonResponse(
                {"status": "success", "indicators": [0] * len(course_ids)}
            )

        # Get all indicators using parallel execution
        with ThreadPoolExecutor(max_workers=8) as executor:  # Increased workers
            futures = [
                executor.submit(relevant_course_name, search_query, courses),
                executor.submit(relevant_department_codes, search_query, courses),
                executor.submit(relevant_department_names, search_query, courses),
                executor.submit(relevant_course_codes, search_query, courses),
                executor.submit(relevant_divisions, search_query, courses),
                executor.submit(relevant_keywords, search_query, courses),
                executor.submit(relevant_descriptions, search_query, courses),
                executor.submit(relevant_professor_names, search_query, courses),
                executor.submit(half_courses, search_query, courses)
        ]
            
            # Get all results at once
            all_results = [future.result() for future in futures]
            
            [
                name_indicators,
                dept_code_indicators,
                dept_name_indicators,
                course_code_indicators,
                division_indicators,
                keyword_indicators,
                description_indicators,
                professor_indicators,
                half_flag
            ] = all_results

        # Calculate final indicators maintaining order
        final_indicators = []
        for idx in range(len(courses)):
            result = (
                name_indicators[idx]
                | dept_code_indicators[idx]
                | dept_name_indicators[idx]
                | course_code_indicators[idx]
                | division_indicators[idx]
                | keyword_indicators[idx]
                | description_indicators[idx]
                | professor_indicators[idx]
            )

            if "half" in search_query:
                result = result and half_flag[idx]

        # if len(search_query) > 5:
            #     result = result or similarity_indicators[idx]

            final_indicators.append(result)

        return JsonResponse({"status": "success", "indicators": final_indicators})

    except Exception as e:
        return JsonResponse(
            {"status": "error", "message": str(e), "indicators": [0] * len(course_ids)},
            status=500,
        )
