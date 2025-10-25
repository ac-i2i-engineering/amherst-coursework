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
    - LOCATION_MATCH_WEIGHT : Weight for section location matches
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

DIVISION_WEIGHT = 8
"""Weight applied to matches in academic division names (e.g., 'Science') - reduced to prevent generic matches"""

KEYWORD_WEIGHT = 70
"""Weight applied to matches in course keywords/tags"""

DESCRIPTION_WEIGHT = 60
"""Weight applied to matches found in course descriptions"""

PROFESSOR_WEIGHT = 130
"""Weight applied to matches in professor names"""

HALF_COURSE_WEIGHT = 200
"""Additional weight applied when 'half' appears in query and course is half-credit"""

SIMILARITY_WEIGHT = 120
"""Multiplier applied to TF-IDF cosine similarity scores for text matching"""

PHRASE_MATCH_WEIGHT = 80
"""Additional weight applied when a multi-word phrase appears together in course text"""

LOCATION_MATCH_WEIGHT = 200
"""Weight applied when course section location matches the location code in query (e.g., 'location/SMUD')"""

SCORE_CUTOFF = 0.25
"""Minimum score threshold as fraction of highest score (0.0 to 1.0) for including a course in results"""

MAX_RESULTS = 100
"""Maximum number of results to return (prevents overwhelming users with too many options)"""

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

# Keyword synonyms for better matching
KEYWORD_SYNONYMS = {
    "coding": ["programming", "computer science", "software"],
    "code": ["programming", "computer science"],
    "climate": ["environmental", "climate change", "global warming"],
    "environment": ["environmental", "climate", "ecology"],
    "film": ["cinema", "movie"],
    "movies": ["film", "cinema"],
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
    Compute TF-IDF cosine similarity scores between a query and a list of information.

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


def expand_synonyms(text: str) -> str:
    """
    Expand keywords with their synonyms for better matching.

    Parameters
    ----------
    text : str
        Input text that may contain keywords

    Returns
    -------
    str
        Text with synonyms added

    Examples
    --------
    >>> expand_synonyms("I want to learn coding")
    "I want to learn coding programming computer science software"
    """
    import re

    expanded = text
    text_lower = text.lower()

    # Add synonyms for matching keywords
    for keyword, synonyms in KEYWORD_SYNONYMS.items():
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, text_lower):
            # Add synonyms after the keyword
            synonym_text = " ".join(synonyms)
            expanded = re.sub(
                pattern, f"{keyword} {synonym_text}", expanded, flags=re.IGNORECASE
            )

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


def score_term_matches(
    term: str, filtered_courses, scores: dict, use_word_boundary: bool = False
) -> None:
    """
    Score courses based on term matches across different fields.

    Parameters
    ----------
    term : str
        Search term to match
    filtered_courses : QuerySet
        Django QuerySet of courses to search
    scores : dict
        Dictionary mapping course IDs to scores (modified in place)
    use_word_boundary : bool
        If True, use word boundary matching for precise matches
    """
    import re

    # Determine matching strategy
    if use_word_boundary:
        word_pattern = r"\b" + re.escape(term) + r"\b"
        match_filter = lambda field: {f"{field}__iregex": word_pattern}
    else:
        match_filter = lambda field: {f"{field}__icontains": term}

    # Score course name matches
    name_matches = filtered_courses.filter(**match_filter("courseName"))
    for course in name_matches:
        scores[course.id] += COURSE_NAME_WEIGHT
        # Bonus for exact word match
        course_words = course.courseName.lower().split()
        if term in course_words:
            scores[course.id] += COURSE_NAME_EXACT_WEIGHT

    # Score department name matches
    dept_matches = filtered_courses.filter(**match_filter("departments__name"))
    for course in dept_matches:
        scores[course.id] += DEPARTMENT_NAME_WEIGHT

    # Score division matches
    div_matches = filtered_courses.filter(**match_filter("divisions__name"))
    for course in div_matches:
        scores[course.id] += DIVISION_WEIGHT

    # Score keyword matches
    keyword_matches = filtered_courses.filter(**match_filter("keywords__name"))
    for course in keyword_matches:
        scores[course.id] += KEYWORD_WEIGHT

    # Score description matches
    desc_matches = filtered_courses.filter(**match_filter("courseDescription"))
    for course in desc_matches:
        scores[course.id] += DESCRIPTION_WEIGHT

    # Score professor matches
    prof_matches = filtered_courses.filter(**match_filter("professors__name"))
    for course in prof_matches:
        scores[course.id] += PROFESSOR_WEIGHT


def score_course_codes(term: str, filtered_courses, scores: dict) -> None:
    """
    Score courses based on course code matches.

    Parameters
    ----------
    term : str
        Search term to match against course codes
    filtered_courses : QuerySet
        Django QuerySet of courses to search
    scores : dict
        Dictionary mapping course IDs to scores (modified in place)
    """
    # Match course codes with partial and formatted matches
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

    # Match department codes
    dept_code_matches = filtered_courses.filter(
        departments__code__iexact=restore_dept_code(term)
    )
    for course in dept_code_matches:
        scores[course.id] += DEPARTMENT_CODE_WEIGHT


def score_phrase_matches(phrases: List[str], filtered_courses, scores: dict) -> None:
    """
    Score courses based on multi-word phrase matches.

    Parameters
    ----------
    phrases : List[str]
        List of phrases to match
    filtered_courses : QuerySet
        Django QuerySet of courses to search
    scores : dict
        Dictionary mapping course IDs to scores (modified in place)
    """
    for phrase in phrases:
        # Expand abbreviations in phrases
        expanded_phrase = expand_abbreviations(phrase)

        # Check original phrase in name and description
        for course in filtered_courses.filter(courseName__icontains=phrase):
            scores[course.id] += PHRASE_MATCH_WEIGHT

        for course in filtered_courses.filter(courseDescription__icontains=phrase):
            scores[course.id] += PHRASE_MATCH_WEIGHT

        # Check expanded phrase if different
        if expanded_phrase != phrase:
            for course in filtered_courses.filter(
                courseName__icontains=expanded_phrase
            ):
                scores[course.id] += PHRASE_MATCH_WEIGHT

            for course in filtered_courses.filter(
                courseDescription__icontains=expanded_phrase
            ):
                scores[course.id] += PHRASE_MATCH_WEIGHT


def score_similarity(
    search_query: str, expanded_query: str, filtered_courses, scores: dict
) -> None:
    """
    Score courses based on TF-IDF similarity.

    Parameters
    ----------
    search_query : str
        Original search query
    expanded_query : str
        Query with abbreviations expanded
    filtered_courses : QuerySet
        Django QuerySet of courses to search
    scores : dict
        Dictionary mapping course IDs to scores (modified in place)
    """
    if len(search_query) > MIN_CHAR_FOR_COS_SIM:
        # Expand abbreviations in course texts for better matching
        course_texts = [
            expand_abbreviations(prepare_course_text(course))
            for course in filtered_courses
        ]

        # TF-IDF similarity
        tfidf_scores = compute_similarity_scores(expanded_query, course_texts)
        for course, score in zip(filtered_courses, tfidf_scores):
            scores[course.id] += score * SIMILARITY_WEIGHT


def score_location_matches(
    search_terms: List[str], filtered_courses, scores: dict
) -> None:
    """
    Score courses based on section location matches.

    Parameters
    ----------
    search_terms : List[str]
        Search terms to match against locations (e.g., ['SMUD', 'KEEF'])
    filtered_courses : QuerySet
        Django QuerySet of courses to search
    scores : dict
        Dictionary mapping course IDs to scores (modified in place)

    Notes
    -----
    Only matches terms that are likely building codes:
    - Must be at least 3 characters long
    - Must contain at least one letter
    - Avoids matching pure numbers (e.g., "207" from "COSC-207")
    """
    import re

    # Check each search term against section locations
    for term in search_terms:
        # Skip terms that are too short or are pure numbers
        # This prevents matching course numbers like "207" from "COSC-207"
        if len(term) < 3:
            continue
        if term.isdigit():
            continue
        # Skip terms that look like course codes (e.g., "COSC-207", "math111")
        if re.match(r"^[A-Z]{4}-?\d+[A-Z]?$", term, re.IGNORECASE):
            continue

        # Match courses that have sections with this term in the location
        # This will match building codes like "SMUD", "KEEF", "WEBS", etc.
        location_matches = filtered_courses.filter(
            sections__location__icontains=term
        ).distinct()

        for course in location_matches:
            scores[course.id] += LOCATION_MATCH_WEIGHT


def apply_score_penalties(filtered_courses, scores: dict, search_query: str) -> None:
    """
    Apply penalties and bonuses to scores based on query context.

    Parameters
    ----------
    filtered_courses : QuerySet
        Django QuerySet of courses to search
    scores : dict
        Dictionary mapping course IDs to scores (modified in place)
    search_query : str
        Original search query for context-aware penalties
    """
    # Keywords that should prioritize specific sciences over social sciences
    stem_keywords = {
        "machine",
        "learning",
        "algorithm",
        "computer",
        "programming",
        "data",
        "mathematics",
        "calculus",
        "algebra",
        "physics",
        "chemistry",
        "biology",
        "engineering",
        "statistics",
        "natural",
    }

    # STEM department codes
    stem_departments = {
        "COSC",
        "PHYS",
        "CHEM",
        "BIOL",
        "BCBP",
        "NEUR",
        "GEOL",
        "ENST",
    }

    query_lower = search_query.lower()
    # Check for STEM keywords, but be more lenient with generic "science" queries
    is_stem_query = any(keyword in query_lower for keyword in stem_keywords)
    is_generic_science_query = "science" in query_lower and not any(
        k in query_lower for k in stem_keywords
    )

    # Check if query explicitly mentions social sciences
    is_social_science_query = any(
        term in query_lower
        for term in [
            "social science",
            "sociology",
            "anthropology",
            "gender",
            "sexuality",
        ]
    )

    for course in filtered_courses:
        if scores[course.id] > 0:
            num_divisions = course.divisions.count()
            if num_divisions > 3:
                # Reduce score for courses in 4+ divisions (likely generic)
                scores[course.id] *= 0.5

            # Get course department codes
            course_dept_codes = set(course.departments.values_list("code", flat=True))
            is_stem_course = bool(course_dept_codes & stem_departments)

            # Boost STEM courses when STEM query is detected
            if is_stem_query and not is_social_science_query and is_stem_course:
                scores[course.id] *= 1.3
            # Also boost STEM courses for generic science queries (but less aggressively)
            elif is_generic_science_query and is_stem_course:
                scores[course.id] *= 1.5

            # Additional penalty for social science courses when STEM query is detected
            # but NOT when user explicitly searches for social sciences
            # and NOT for generic science queries (too broad)
            if (
                is_stem_query
                and not is_social_science_query
                and not is_generic_science_query
            ):
                course_text = prepare_course_text(course).lower()
                social_science_indicators = [
                    "social science",
                    "sociology",
                    "anthropology",
                    "gender studies",
                    "women studies",
                    "sexuality",
                    "educational equity",
                    "feminist studies",
                ]
                if any(
                    indicator in course_text for indicator in social_science_indicators
                ):
                    # Strong penalty for social sciences in STEM queries
                    scores[course.id] *= 0.25


def filter_by_score_threshold(courses: List[Course], scores: dict) -> List[Course]:
    """
    Filter and sort courses by score, applying cutoff threshold.

    Parameters
    ----------
    courses : List[Course]
        List of all courses
    scores : dict
        Dictionary mapping course IDs to scores

    Returns
    -------
    List[Course]
        Filtered and sorted list of courses above threshold
    """
    # Build list of (course, score) tuples
    scored_courses = []
    for course in courses:
        score = scores.get(course.id, 0)
        if score > 0:
            scored_courses.append((course, score))

    # Sort by score descending
    scored_courses.sort(key=lambda x: x[1], reverse=True)

    # Apply cutoff threshold
    if scored_courses:
        highest_score = scored_courses[0][1]
        scored_courses = [
            course
            for course, score in scored_courses
            if score / highest_score >= SCORE_CUTOFF
        ]
        # Limit to MAX_RESULTS to avoid overwhelming users
        scored_courses = scored_courses[:MAX_RESULTS]
    else:
        scored_courses = []

    return scored_courses


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
    - Location matching: search terms are checked against section locations (e.g., "SMUD", "WEBS", "207")
    - Abbreviation expansion (e.g., "AI" -> "artificial intelligence")
    - Phrase detection for multi-word queries
    - Longer queries (>5 chars) use cosine similarity

    Examples
    --------
    >>> filter("computer science SMUD", courses)
    # Returns computer science courses with sections in SMUD building, boosted to top

    >>> filter("intro physics KEEF", courses)
    # Returns intro physics courses with sections in KEEF building, boosted to top
    """
    if not search_query:
        return [(course, 1.0) for course in courses]

    # Expand synonyms first (e.g., "coding" -> "coding programming computer science")
    synonym_expanded = expand_synonyms(search_query)
    # Then expand abbreviations
    expanded_query = expand_abbreviations(synonym_expanded)
    search_terms = clean_query(expanded_query)

    # Detect meaningful phrases in the original query
    phrases = detect_phrases(search_query)

    # Start with all courses
    filtered_courses = Course.objects.filter(
        id__in=[course.id for course in courses]
    ).prefetch_related(
        "courseCodes", "departments", "divisions", "keywords", "professors", "sections"
    )

    # Initialize scores dictionary
    scores = {course.id: 0.0 for course in courses}

    # Check if query is looking for intro courses
    query_lower = search_query.lower()
    wants_intro = any(
        word in query_lower for word in ["intro", "introduction", "beginner", "start"]
    )

    # Score each search term
    for term in search_terms:
        if term == "half":
            # Special handling for half courses
            half_courses = filtered_courses.filter(id__regex=r"^.{3}1")
            for course in half_courses:
                scores[course.id] += HALF_COURSE_WEIGHT
            continue

        # Use word boundary matching for short terms to avoid false matches
        use_word_boundary = len(term) <= 3

        # Score term matches across all fields
        score_term_matches(term, filtered_courses, scores, use_word_boundary)

        # Score course code matches (always uses special handling)
        score_course_codes(term, filtered_courses, scores)

    # Boost intro courses if query suggests beginner interest
    if wants_intro:
        intro_courses = filtered_courses.filter(
            Q(courseName__icontains="introduction")
            | Q(courseName__icontains="intro")
            | Q(courseDescription__icontains="introductory")
        )
        for course in intro_courses:
            if scores[course.id] > 0:
                scores[course.id] *= 1.5

    # Score phrase matches
    score_phrase_matches(phrases, filtered_courses, scores)

    # Score similarity for longer queries
    score_similarity(search_query, expanded_query, filtered_courses, scores)

    # Score location matches for all search terms
    score_location_matches(search_terms, filtered_courses, scores)

    # Apply penalties for generic courses
    apply_score_penalties(filtered_courses, scores, search_query)

    # Filter and sort by score threshold
    return filter_by_score_threshold(courses, scores)
