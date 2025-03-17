Filters
=======
Course filtering and ranking module with configurable search weights.

This module provides functionality for filtering and ranking courses based on 
search queries, using a weighted scoring system for different match types.

Constants
---------

.. py:data:: MIN_CHAR_FOR_COS_SIM
   :type: int

   Minimum characters required in search query before applying cosine similarity matching

.. py:data:: DEPARTMENT_NAME_WEIGHT
   :type: int

   Weight applied to matches found in department names (e.g., 'Computer Science')

.. py:data:: COURSE_NAME_WEIGHT
   :type: int

   Weight applied to matches found in course titles

.. py:data:: COURSE_CODE_WEIGHT
   :type: int

   Weight applied to matches in course codes (e.g., 'COSC-111')

.. py:data:: DEPARTMENT_CODE_WEIGHT
   :type: int

   Weight applied to matches in department codes (e.g., 'COSC')

.. py:data:: DIVISION_WEIGHT
   :type: int

   Weight applied to matches in academic division names (e.g., 'Science')

.. py:data:: KEYWORD_WEIGHT
   :type: int

   Weight applied to matches in course keywords/tags

.. py:data:: DESCRIPTION_WEIGHT
   :type: int

   Weight applied to matches found in course descriptions

.. py:data:: PROFESSOR_WEIGHT
   :type: int

   Weight applied to matches in professor names

.. py:data:: HALF_COURSE_WEIGHT
   :type: int

   Additional weight applied when 'half' appears in query and course is half-credit

.. py:data:: SIMILARITY_WEIGHT
   :type: int

   Multiplier applied to cosine similarity scores for text matching

.. py:data:: SCORE_CUTOFF
   :type: float

   Minimum score threshold as fraction of highest score (0.0 to 1.0) for including a course in results

Functions
---------

.. autofunction:: amherst_coursework_algo.masked_filters.restore_dept_code
.. autofunction:: amherst_coursework_algo.masked_filters.restore_course_code
.. autofunction:: amherst_coursework_algo.masked_filters.prepare_course_text
.. autofunction:: amherst_coursework_algo.masked_filters.compute_similarity_scores
.. autofunction:: amherst_coursework_algo.masked_filters.clean_query
.. autofunction:: amherst_coursework_algo.masked_filters.filter
