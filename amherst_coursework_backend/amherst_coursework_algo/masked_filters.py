"""
Course filtering and ranking module with configurable search weights.

This module provides functionality for filtering and ranking courses based on
search queries, using a weighted scoring system for different match types.

Constants
---------
This module uses several constants to control the filtering and ranking behavior:

Scoring Weights:
    - DEPARTMENT_NAME_WEIGHT : Weight for department name matches
    - COURSE_NAME_WEIGHT : Weight for course name matches
    - COURSE_CODE_WEIGHT : Weight for course code matches
    - DEPARTMENT_CODE_WEIGHT : Weight for department code matches
    - DIVISION_WEIGHT : Weight for division matches
    - KEYWORD_WEIGHT : Weight for keyword matches
    - DESCRIPTION_WEIGHT : Weight for description matches
    - PROFESSOR_WEIGHT : Weight for professor name matches
    - HALF_COURSE_WEIGHT : Weight for half-credit courses
    - SIMILARITY_WEIGHT : Weight for cosine similarity scores

Configuration:
    - SCORE_CUTOFF : Minimum score threshold for results
    - MIN_CHAR_FOR_COS_SIM : Minimum query length for similarity search

Functions
---------
The module provides the following main functions:

- restore_dept_code : Normalizes department codes
- restore_course_code : Formats course codes
- prepare_course_text : Prepares course text for similarity search
- compute_similarity_scores : Calculates similarity between texts
- clean_query : Processes and tokenizes search queries
- filter : Main filtering and ranking function
"""

from .models import Course
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import List
from django.db.models import Q
import nltk
from nltk.corpus import stopwords

courses = []

# =============================================================================
# Constants
# =============================================================================

MIN_CHAR_FOR_COS_SIM = 3
"""Minimum characters required in search query before applying cosine similarity matching"""

# Scoring Weights
DEPARTMENT_NAME_WEIGHT = 120
"""Weight applied to matches found in department names (e.g., 'Computer Science')"""

COURSE_NAME_WEIGHT = 100
"""Weight applied to matches found in course titles"""

COURSE_NAME_EXACT_WEIGHT = 150
"""Weight applied to exact word matches in course titles (bonus added to COURSE_NAME_WEIGHT)"""

COURSE_CODE_WEIGHT = 90
"""Weight applied to partial matches in course codes (e.g., 'COSC' in 'COSC-111')"""

COURSE_CODE_EXACT_WEIGHT = 300
"""Weight applied to exact course code matches (e.g., query 'COSC-111' matches 'COSC-111')"""

DEPARTMENT_CODE_WEIGHT = 150
"""Weight applied to matches in department codes (e.g., 'COSC')"""

DIVISION_WEIGHT = 15
"""Weight applied to matches in academic division names (e.g., 'Science')"""

KEYWORD_WEIGHT = 70
"""Weight applied to matches in course keywords/tags"""

DESCRIPTION_WEIGHT = 60
"""Weight applied to matches found in course descriptions"""

PROFESSOR_WEIGHT = 130
"""Weight applied to matches in professor names"""

HALF_COURSE_WEIGHT = 200
"""Additional weight applied when 'half' appears in query and course is half-credit"""

SIMILARITY_WEIGHT = 180
"""Multiplier applied to cosine similarity scores for text matching"""

PHRASE_MATCH_WEIGHT = 80
"""Additional weight applied when a multi-word phrase appears together in course text"""

SCORE_CUTOFF = 0.20
"""Minimum score threshold as fraction of highest score (0.0 to 1.0) for including a course in results"""

# Common abbreviations and their expansions for semantic matching
ABBREVIATION_MAP = {
    "ai": "artificial intelligence",
    "ml": "machine learning",
    "nlp": "natural language processing",
    "dl": "deep learning",
    "cv": "computer vision",
    "rl": "reinforcement learning",
    "nn": "neural network",
    "cnn": "convolutional neural network",
    "rnn": "recurrent neural network",
}

# Initialize stopwords for English
try:
    stop_words = set(stopwords.words("english"))
except LookupError as e:
    try:
        nltk.download("stopwords")
        stop_words = set(stopwords.words("english"))
    except Exception as download_error:
        raise RuntimeError(
            f"Failed to initialize stopwords: {str(e)}. Download attempt failed: {str(download_error)}"
        )


# =============================================================================
# Functions
# =============================================================================


def restore_dept_code(code: str) -> str:
    """
    Extract and normalize department code from various formats.

    Parameters
    ----------
    code : str
        Input string containing potential department code

    Returns
    -------
    str
        Normalized 4-letter department code or 'XXXXX' if invalid

    Examples
    --------
    >>> restore_dept_code('math')
    'MATH'
    >>> restore_dept_code('math1')
    'MATH'
    >>> restore_dept_code('mat')
    'XXXXX'
    >>> restore_dept_code('maths')
    'XXXXX'
    >>> restore_dept_code('123')
    'XXXXX'
    """
    import re

    # Get only letters from start of string
    match = re.match(r"^([a-zA-Z]+)", code)
    if not match:
        return "XXXXX"

    dept = match.group(1)
    if len(dept) != 4:
        return "XXXXX"

    return dept.upper()


def restore_course_code(code: str) -> str:
    """
    Restore a course code pattern by adding a hyphen between department and number.

    Parameters
    ----------
    code : str
        Input string containing potential course code

    Returns
    -------
    str
        Formatted course code with hyphen or original string if invalid format

    Examples
    --------
    >>> restore_course_code('math111')
    'MATH-111'
    >>> restore_course_code('invalid')
    'invalid'
    """
    import re

    match = re.match(r"([a-zA-Z]+)(\d+)", code)
    if not match:
        return code

    dept, number = match.groups()
    return f"{dept.upper()}-{number}"


def prepare_course_text(course) -> str:
    """
    Prepare a concatenated text representation of course information for similarity search.

    Parameters
    ----------
    course : Course
        Course object containing related information

    Returns
    -------
    str
        Space-separated string containing course name, description, departments,
        professors, and keywords in lowercase

    Notes
    -----
    Handles null values by using empty strings as fallbacks
    """
    return " ".join(
        [
            course.courseName or "",
            course.courseDescription or "",
            " ".join(dept.name for dept in course.departments.all()),
            " ".join(prof.name for prof in course.professors.all()),
            " ".join(keyword.name for keyword in course.keywords.all()),
        ]
    ).lower()


def compute_similarity_scores(query: str, information: List[str]) -> List[float]:
    """
    Compute cosine similarity scores between a query and a list of information.

    Parameters
    ----------
    query : str
        The input query string to compare against the information
    information : List[str]
        List of text strings to compare with the query

    Returns
    -------
    List[float]
        List of similarity scores between 0 and 1, where higher values indicate
        greater similarity

    Notes
    -----
    - Uses TF-IDF vectorization and cosine similarity
    - Removes English stop words before computation
    - Returns list of zeros if query or information is empty
    - DOES NOT compare semantic similarity of text, only lexical similarity

    Examples
    --------
    >>> info = ["AI in Healthcare", "Machine Learning Workshop"]
    >>> compute_similarity_scores("Healthcare AI", info)
    [0.72, 0]  # Example scores, actual values may vary
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


def expand_abbreviations(text: str) -> str:
    """
    Expand common abbreviations in text for better semantic matching.
    Works bidirectionally: expands abbreviations AND adds abbreviations for full terms.

    Parameters
    ----------
    text : str
        Input text that may contain abbreviations or full terms

    Returns
    -------
    str
        Text with abbreviations expanded and full terms abbreviated (original + both forms)

    Examples
    --------
    >>> expand_abbreviations("AI and ML course")
    "AI artificial intelligence and ML machine learning course"
    >>> expand_abbreviations("artificial intelligence course")
    "artificial intelligence AI course"
    """
    import re

    expanded = text

    # First pass: expand abbreviations to full terms
    for abbr, full in ABBREVIATION_MAP.items():
        # Match abbreviation as whole word (case-insensitive)
        pattern = r"\b" + re.escape(abbr) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            # Add expanded form after the abbreviation
            expanded = re.sub(pattern, f"{abbr} {full}", expanded, flags=re.IGNORECASE)

    # Second pass: add abbreviations for full terms
    for abbr, full in ABBREVIATION_MAP.items():
        # Match full term (case-insensitive)
        pattern = r"\b" + re.escape(full) + r"\b"
        if re.search(pattern, expanded, re.IGNORECASE):
            # Add abbreviation after the full term
            expanded = re.sub(pattern, f"{full} {abbr}", expanded, flags=re.IGNORECASE)

    return expanded


def detect_phrases(query: str) -> List[str]:
    """
    Detect meaningful multi-word phrases in a query.

    Parameters
    ----------
    query : str
        Search query string

    Returns
    -------
    List[str]
        List of detected phrases (2-3 word combinations)

    Examples
    --------
    >>> detect_phrases("artificial intelligence and ethics")
    ["artificial intelligence", "intelligence and ethics"]
    """
    words = query.lower().split()
    phrases = []

    # Look for 2-word phrases
    for i in range(len(words) - 1):
        if words[i] not in stop_words and words[i + 1] not in stop_words:
            phrases.append(f"{words[i]} {words[i+1]}")

    # Look for 3-word phrases (skip middle word if it's a stopword)
    for i in range(len(words) - 2):
        if words[i] not in stop_words and words[i + 2] not in stop_words:
            if words[i + 1] in stop_words:
                # e.g., "artificial [and] intelligence"
                phrases.append(f"{words[i]} {words[i+2]}")
            else:
                # e.g., "machine learning algorithms"
                phrases.append(f"{words[i]} {words[i+1]} {words[i+2]}")

    return phrases


def clean_query(query: str) -> List[str]:
    """
    Clean and tokenize a search query string.

    Parameters
    ----------
    query : str
        Raw input query string

    Returns
    -------
    List[str]
        List of cleaned, lowercase words with stop words and non-alphanumeric
        characters removed

    Notes
    -----
    Uses NLTK's English stop words list for filtering
    """
    return [
        word.lower()
        for word in query.split()
        if (word.isalnum() or "-" in word) and word.lower() not in stop_words
    ]


def filter(search_query: str, courses: List[Course]) -> List[Course]:
    """
    Filter and rank courses based on search query relevance.

    Parameters
    ----------
    search_query : str
        User's search query string
    courses : List[Course]
        List of Course objects to filter

    Returns
    -------
    List[Course]
        Filtered and ranked list of courses that match the search criteria

    Notes
    -----
    Global scoring weights defined at module level:
    - DEPARTMENT_NAME_WEIGHT : Weight for department name matches
    - COURSE_NAME_WEIGHT : Weight for course name matches
    - COURSE_CODE_WEIGHT : Weight for course code matches
    - DEPARTMENT_CODE_WEIGHT : Weight for department code matches
    - DIVISION_WEIGHT : Weight for division matches
    - KEYWORD_WEIGHT : Weight for keyword matches
    - DESCRIPTION_WEIGHT : Weight for description matches
    - PROFESSOR_WEIGHT : Weight for professor name matches
    - HALF_COURSE_WEIGHT : Weight for half-credit courses
    - SIMILARITY_WEIGHT : Weight for cosine similarity scores
    - PHRASE_MATCH_WEIGHT : Weight for multi-word phrase matches

    Global configuration:
    - SCORE_CUTOFF : Courses below this fraction of the highest score are filtered out
    - MIN_CHAR_FOR_COS_SIM : Minimum query length for cosine similarity search

    Special handling for:
    - "half" keyword to filter half-credit courses
    - Abbreviation expansion (e.g., "AI" -> "artificial intelligence")
    - Phrase detection for multi-word queries
    - Longer queries (>5 chars) use cosine similarity
    """
    if not search_query:
        return [(course, 1.0) for course in courses]

    # Expand abbreviations in the query for better matching
    expanded_query = expand_abbreviations(search_query)
    search_terms = clean_query(expanded_query)

    # Detect meaningful phrases in the original query
    phrases = detect_phrases(search_query)

    # Start with all courses
    filtered_courses = Course.objects.filter(
        id__in=[course.id for course in courses]
    ).prefetch_related(
        "courseCodes", "departments", "divisions", "keywords", "professors"
    )

    # Initialize scores dictionary
    scores = {course.id: 0.0 for course in courses}

    for term in search_terms:
        if term == "half":
            # Special handling for half courses
            half_courses = filtered_courses.filter(id__regex=r"^.{3}1")
            for course in half_courses:
                scores[course.id] += HALF_COURSE_WEIGHT
            continue

        # Use word boundary matching for short terms (2-3 chars) to avoid false matches
        # e.g., "ai" shouldn't match "said", "detail", "email"
        use_word_boundary = len(term) <= 3

        if use_word_boundary:
            import re

            # Create regex pattern with word boundaries
            word_pattern = r"\b" + re.escape(term) + r"\b"

            # Calculate scores for each matching field with word boundaries
            name_matches = filtered_courses.filter(courseName__iregex=word_pattern)
            for course in name_matches:
                scores[course.id] += COURSE_NAME_WEIGHT
                # Bonus for exact word match in course name
                course_words = course.courseName.lower().split()
                if term in course_words:
                    scores[course.id] += COURSE_NAME_EXACT_WEIGHT

            dept_matches = filtered_courses.filter(
                departments__name__iregex=word_pattern
            )
            for course in dept_matches:
                scores[course.id] += DEPARTMENT_NAME_WEIGHT

            div_matches = filtered_courses.filter(divisions__name__iregex=word_pattern)
            for course in div_matches:
                scores[course.id] += DIVISION_WEIGHT

            keyword_matches = filtered_courses.filter(
                keywords__name__iregex=word_pattern
            )
            for course in keyword_matches:
                scores[course.id] += KEYWORD_WEIGHT

            desc_matches = filtered_courses.filter(
                courseDescription__iregex=word_pattern
            )
            for course in desc_matches:
                scores[course.id] += DESCRIPTION_WEIGHT

            prof_matches = filtered_courses.filter(
                professors__name__iregex=word_pattern
            )
            for course in prof_matches:
                scores[course.id] += PROFESSOR_WEIGHT
        else:
            # Use regular icontains for longer terms
            name_matches = filtered_courses.filter(courseName__icontains=term)
            for course in name_matches:
                scores[course.id] += COURSE_NAME_WEIGHT
                # Bonus for exact word match in course name
                course_words = course.courseName.lower().split()
                if term in course_words:
                    scores[course.id] += COURSE_NAME_EXACT_WEIGHT

            dept_matches = filtered_courses.filter(departments__name__icontains=term)
            for course in dept_matches:
                scores[course.id] += DEPARTMENT_NAME_WEIGHT

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

        # Course code matching (always use special handling)
        code_matches = filtered_courses.filter(
            Q(courseCodes__value__icontains=term)
            | Q(courseCodes__value__iregex=restore_course_code(term))
        )
        for course in code_matches.distinct():
            scores[course.id] += COURSE_CODE_WEIGHT
            # Bonus for exact course code match
            for code in course.courseCodes.all():
                if code.value.upper() == term.upper():
                    scores[course.id] += COURSE_CODE_EXACT_WEIGHT
                    break

        dept_code_matches = filtered_courses.filter(
            departments__code__iexact=restore_dept_code(term)
        )
        for course in dept_code_matches:
            scores[course.id] += DEPARTMENT_CODE_WEIGHT

    # Add bonus for phrase matches
    for phrase in phrases:
        # Expand abbreviations in phrases too
        expanded_phrase = expand_abbreviations(phrase)

        # Check if phrase appears in course name or description
        phrase_in_name = filtered_courses.filter(courseName__icontains=phrase)
        for course in phrase_in_name:
            scores[course.id] += PHRASE_MATCH_WEIGHT

        phrase_in_desc = filtered_courses.filter(courseDescription__icontains=phrase)
        for course in phrase_in_desc:
            scores[course.id] += PHRASE_MATCH_WEIGHT

        # Also check expanded phrase
        if expanded_phrase != phrase:
            phrase_in_name_exp = filtered_courses.filter(
                courseName__icontains=expanded_phrase
            )
            for course in phrase_in_name_exp:
                scores[course.id] += PHRASE_MATCH_WEIGHT

            phrase_in_desc_exp = filtered_courses.filter(
                courseDescription__icontains=expanded_phrase
            )
            for course in phrase_in_desc_exp:
                scores[course.id] += PHRASE_MATCH_WEIGHT

    # Add similarity search for longer queries
    if len(search_query) > MIN_CHAR_FOR_COS_SIM:
        # Expand abbreviations in course texts for better matching
        course_texts = [
            expand_abbreviations(prepare_course_text(course))
            for course in filtered_courses
        ]
        # Use expanded query for similarity comparison
        similarity_scores = compute_similarity_scores(expanded_query, course_texts)
        for course, score in zip(filtered_courses, similarity_scores):
            scores[course.id] += score * SIMILARITY_WEIGHT

    # Apply penalty for overly generic courses (in many divisions)
    for course in filtered_courses:
        if scores[course.id] > 0:
            num_divisions = course.divisions.count()
            if num_divisions > 3:
                # Reduce score for courses in 4+ divisions (likely generic)
                scores[course.id] *= 0.5

    scored_courses = []
    for course in courses:
        score = scores.get(course.id, 0)
        if score > 0:
            scored_courses.append((course, score))

    # Sort by score in descending order
    scored_courses.sort(key=lambda x: x[1], reverse=True)

    highest_score = scored_courses[0][1] if scored_courses else 1
    scored_courses = [
        course
        for course, score in scored_courses
        if score / highest_score >= SCORE_CUTOFF
    ]

    return scored_courses
