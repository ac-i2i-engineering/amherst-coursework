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
from django.db.models import Case, When, F, FloatField, Value
from django.db.models import Q
import nltk
from nltk.corpus import stopwords

courses = []
MIN_CHAR_FOR_COS_SIM = 11

DEPARTMENT_NAME_WEIGHT = 90
COURSE_NAME_WEIGHT = 90
COURSE_CODE_WEIGHT = 90
DEPT_CODE_WEIGHT = 70
DIVISION_WEIGHT = 40
KEYWORD_WEIGHT = 40
DESCRIPTION_WEIGHT = 50
PROFESSOR_WEIGHT = 50
HALF_COURSE_WEIGHT = 200  # not sure what weight to use here, want it to be strong enough so that it is not ignored, but not so strong that all other non half courses are ignored
SIMILARITY_WEIGHT = 160

SIMILARITY_THRESHOLD = 0.1

SCORE_CUTOFF = 80

try:
    stop_words = set(stopwords.words("english"))
except LookupError:
    nltk.download("stopwords")
    stop_words = set(stopwords.words("english"))


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


def clean_query(query: str) -> List[str]:
    """
    Clean the query string by removing special characters and splitting into words.

    Parameters
    ----------
    query : str
        The input query string to be cleaned.

    Returns
    -------
    List[str]
        A list of cleaned words extracted from the query string.
    """
    return [
        word.lower()
        for word in query.split()
        if word.isalnum() and word.lower() not in stop_words
    ]


def filter(search_query: str, courses: List[Course]) -> List[tuple[Course, float]]:
    """
    Filter courses based on search query using Django's built-in filters.
    Returns courses with their relevance scores.
    """
    if not search_query:
        return [(course, 1.0) for course in courses]

    search_terms = search_query.lower().split()

    # Start with all courses
    filtered_courses = Course.objects.filter(id__in=[course.id for course in courses])

    # Initialize scores dictionary
    scores = {course.id: 0.0 for course in courses}

    for term in search_terms:
        if term == "half":
            # Special handling for half courses
            half_courses = filtered_courses.filter(id__regex=r"^.{3}1")
            for course in half_courses:
                scores[course.id] += HALF_COURSE_WEIGHT
            continue

        # Calculate scores for each matching field
        name_matches = filtered_courses.filter(courseName__icontains=term)
        for course in name_matches:
            scores[course.id] += COURSE_NAME_WEIGHT

        dept_matches = filtered_courses.filter(departments__name__icontains=term)
        for course in dept_matches:
            scores[course.id] += DEPARTMENT_NAME_WEIGHT

        code_matches = filtered_courses.filter(
            Q(courseCodes__value__icontains=term)
            | Q(
                courseCodes__value__in=[
                    code.value
                    for course in filtered_courses.all()
                    for code in course.courseCodes.all()
                    if normalize_code(term).lower()
                    in normalize_code(code.value).lower()
                ]
            )
        )
        for course in code_matches.distinct():
            scores[course.id] += COURSE_CODE_WEIGHT

        dept_code_matches = filtered_courses.filter(
            id__in=[
                course.id
                for course in filtered_courses
                for dept in course.departments.all()
                if dept.code.lower() in term.lower()
            ]
        )
        for course in dept_code_matches:
            scores[course.id] += DEPT_CODE_WEIGHT

        div_matches = filtered_courses.filter(divisions__name__icontains=term)
        for course in div_matches:
            scores[course.id] += DIVISION_WEIGHT

        keyword_matches = filtered_courses.filter(keywords__name__icontains=term)
        for course in keyword_matches:
            scores[course.id] += KEYWORD_WEIGHT

        desc_matches = filtered_courses.filter(courseDescription__icontains=term)
        for course in desc_matches:
            scores[course.id] += DESCRIPTION_WEIGHT

        prof_matches = filtered_courses.filter(professors__name__icontains=term)
        for course in prof_matches:
            scores[course.id] += PROFESSOR_WEIGHT

    # Add similarity search for longer queries
    if len(search_query) > MIN_CHAR_FOR_COS_SIM:
        for course in filtered_courses:
            similarity_score = query_course_similarity(search_query, course)
            scores[course.id] += similarity_score * SIMILARITY_WEIGHT

    # Create list of (course, score) tuples
    # scored_courses = [
    #     (course, scores[course.id]) for course in courses if scores[course.id] >= SCORE_CUTOFF
    # ]

    # Create list of (course, score) tuples with debug information
    scored_courses = []
    for course in courses:
        score = scores[course.id]
        if score > 0:
            print(f"\nCourse: {course.courseName} (ID: {course.id})")
            for term in search_terms:
                if term == "half":
                    if str(course.id)[3] == "1":
                        print(f"  Half course match: +{HALF_COURSE_WEIGHT}")
                    continue

                # Print individual match components
                if filtered_courses.filter(
                    id=course.id, courseName__icontains=term
                ).exists():
                    print(f"  Course name match ({term}): +{COURSE_NAME_WEIGHT}")

                if filtered_courses.filter(
                    id=course.id, departments__name__icontains=term
                ).exists():
                    print(
                        f"  Department name match ({term}): +{DEPARTMENT_NAME_WEIGHT}"
                    )

                if filtered_courses.filter(
                    id=course.id, courseCodes__value__icontains=term
                ).exists():
                    print(f"  Course code match ({term}): +{COURSE_CODE_WEIGHT}")

                if filtered_courses.filter(
                    id=course.id, divisions__name__icontains=term
                ).exists():
                    print(f"  Division match ({term}): +{DIVISION_WEIGHT}")

                if filtered_courses.filter(
                    id=course.id, keywords__name__icontains=term
                ).exists():
                    print(f"  Keyword match ({term}): +{KEYWORD_WEIGHT}")

                if filtered_courses.filter(
                    id=course.id, courseDescription__icontains=term
                ).exists():
                    print(f"  Description match ({term}): +{DESCRIPTION_WEIGHT}")

                if filtered_courses.filter(
                    id=course.id, professors__name__icontains=term
                ).exists():
                    print(f"  Professor match ({term}): +{PROFESSOR_WEIGHT}")

            if len(search_query) > MIN_CHAR_FOR_COS_SIM:
                similarity_score = query_course_similarity(search_query, course)
                if similarity_score > 0:
                    print(
                        f"  Similarity score: +{similarity_score * SIMILARITY_WEIGHT:.2f}"
                    )

            print(f"  Total score: {score:.2f}")
            scored_courses.append((course, score))

    # Sort by score in descending order
    scored_courses.sort(key=lambda x: x[1], reverse=True)

    # Sort by score in descending order
    scored_courses.sort(key=lambda x: x[1], reverse=True)

    return [course for course, _ in scored_courses]
