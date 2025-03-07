from django.test import TestCase, Client
from amherst_coursework_algo.models import (
    Course,
    Department,
    CourseCode,
    Division,
    Keyword,
    Professor,
)
from amherst_coursework_algo.masked_filters import (
    normalize_code,
    relevant_course_name,
    relevant_department_codes,
    relevant_department_names,
    relevant_course_codes,
    relevant_divisions,
    relevant_keywords,
    relevant_descriptions,
    half_courses,
    compute_similarity_scores,
)
import json


class TestMaskedFilters(TestCase):
    def setUp(self):
        # Create test departments
        self.dept = Department.objects.create(name="Computer Science", code="COSC")

        # Create test course with explicit id
        self.course = Course.objects.create(
            id=1000000,  # Add explicit id
            courseName="Introduction to Programming",
            courseDescription="Learn Python programming",
        )
        self.course.departments.add(self.dept)

        # Create course code
        code = CourseCode.objects.create(value="COSC-111")

        self.course.courseCodes.add(code)

        # Create division
        self.division = Division.objects.create(name="Science")
        self.course.divisions.add(self.division)

        # Create keyword
        self.keyword = Keyword.objects.create(name="Programming")
        self.course.keywords.add(self.keyword)

        # Create professor
        self.professor = Professor.objects.create(name="John Doe")
        self.course.professors.add(self.professor)

    def test_normalize_code(self):
        """Test code normalization"""
        self.assertEqual(normalize_code("COSC-111"), "COSC111")
        self.assertEqual(normalize_code("MATH 111"), "MATH111")

    def test_relevant_course_name(self):
        """Test course name matching"""
        courses = [self.course]
        self.assertEqual(relevant_course_name("programming", courses), [1])
        self.assertEqual(relevant_course_name("history", courses), [0])

    def test_relevant_department_codes(self):
        """Test department code matching"""
        courses = [self.course]
        self.assertEqual(relevant_department_codes("cosc", courses), [1])
        self.assertEqual(relevant_department_codes("math", courses), [0])

    def test_relevant_department_names(self):
        """Test department name matching"""
        courses = [self.course]
        self.assertEqual(relevant_department_names("computer", courses), [1])
        self.assertEqual(relevant_department_names("mathematics", courses), [0])

    def test_relevant_course_codes(self):
        """Test course code matching"""
        courses = [self.course]
        self.assertEqual(relevant_course_codes("cosc111", courses), [1])
        self.assertEqual(relevant_course_codes("math111", courses), [0])

    def test_relevant_divisions(self):
        """Test division matching"""
        courses = [self.course]
        self.assertEqual(relevant_divisions("science", courses), [1])
        self.assertEqual(relevant_divisions("humanities", courses), [0])

    def test_relevant_keywords(self):
        """Test keyword matching"""
        courses = [self.course]
        self.assertEqual(relevant_keywords("programming", courses), [1])
        self.assertEqual(relevant_keywords("database", courses), [0])

    def test_relevant_descriptions(self):
        """Test description matching"""
        courses = [self.course]
        self.assertEqual(relevant_descriptions("python", courses), [1])
        self.assertEqual(relevant_descriptions("javascript", courses), [0])

    def test_half_courses(self):
        """Test half course filtering"""
        courses = [self.course]
        self.assertEqual(half_courses("half course", courses), [0])
        self.assertEqual(half_courses("full course", courses), [1])

    def test_compute_similarity_scores(self):
        """Test similarity score computation"""
        information = ["Introduction to Programming", "Advanced Algorithms"]
        scores = compute_similarity_scores("programming introduction", information)

        # Check if scores are floats between 0 and 1
        for i, score in enumerate(scores):
            self.assertTrue(
                isinstance(score, float), f"Score at index {i} is not a float: {score}"
            )
            self.assertTrue(
                0 <= score <= 1.00001,
                f"Score at index {i} is not between 0 and 1: {score}",
            )

        # First document should have higher similarity
        self.assertTrue(scores[0] > scores[1])

    def test_empty_inputs(self):
        """Test handling of empty inputs"""
        courses = []
        self.assertEqual(relevant_course_name("test", courses), [])
        self.assertEqual(relevant_department_codes("test", courses), [])
        self.assertEqual(compute_similarity_scores("", ["test"]), [0])
        self.assertEqual(compute_similarity_scores("test", []), [])

    def test_filter_combined(self):
        """Test the filter function with all types of searches combined"""

        # Create mock request data for each type of search we've already tested
        test_queries = [
            {
                "name": "Course name search",
                "query": "programming",
                "should_match": True,
            },
            {"name": "Department code search", "query": "cosc", "should_match": True},
            {
                "name": "Department name search",
                "query": "computer science",
                "should_match": True,
            },
            {"name": "Course code search", "query": "cosc111", "should_match": True},
            {"name": "Division search", "query": "science", "should_match": True},
            {"name": "Keyword search", "query": "programming", "should_match": True},
            {"name": "Description search", "query": "python", "should_match": True},
            {
                "name": "Non-matching search",
                "query": "chemistry",
                "should_match": False,
            },
        ]

        client = Client()

        for test_case in test_queries:
            # Prepare request data
            request_data = {
                "search_query": test_case["query"],
                "course_ids": [self.course.id],
                "similarity_threshold": 0.1,
            }

            # Make request to filter endpoint
            response = client.post(
                "/api/masked_filter/",
                data=json.dumps(request_data),
                content_type="application/json",
            )

            # Check response
            self.assertEqual(
                response.status_code, 200, f"Failed on {test_case['name']}"
            )

            data = json.loads(response.content)
            self.assertIn(
                "indicators", data, f"No indicators in response for {test_case['name']}"
            )

            # For matching queries, indicator should be 1; for non-matching, 0
            expected_indicator = 1 if test_case["should_match"] else 0
            self.assertEqual(
                data["indicators"][0],
                expected_indicator,
                f"Failed {test_case['name']}: expected {expected_indicator} but got {data['indicators'][0]}",
            )

    def tearDown(self):
        """Clean up test data"""
        Course.objects.all().delete()
        Department.objects.all().delete()
        CourseCode.objects.all().delete()
        Division.objects.all().delete()
        Keyword.objects.all().delete()
        Professor.objects.all().delete()
