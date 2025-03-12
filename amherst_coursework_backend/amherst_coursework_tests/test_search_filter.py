from django.test import TestCase
from amherst_coursework_algo.masked_filters import (
    restore_dept_code,
    restore_course_code,
    clean_query,
    compute_similarity_scores,
    filter,
)
from amherst_coursework_algo.models import (
    Course,
    Department,
    Division,
    Professor,
    Keyword,
    CourseCode,
)


class TestRestoreDeptCode(TestCase):
    def test_valid_department_codes(self):
        """Test valid department code patterns"""
        self.assertEqual(restore_dept_code("math"), "MATH")
        self.assertEqual(restore_dept_code("COSC"), "COSC")
        self.assertEqual(restore_dept_code("math1"), "MATH")
        self.assertEqual(restore_dept_code("STAT-231"), "STAT")

    def test_invalid_department_codes(self):
        """Test invalid department code patterns"""
        self.assertEqual(restore_dept_code("mat"), "XXXXX")  # too short
        self.assertEqual(restore_dept_code("maths"), "XXXXX")  # too long
        self.assertEqual(restore_dept_code("123"), "XXXXX")  # only numbers
        self.assertEqual(restore_dept_code(""), "XXXXX")  # empty string


class TestRestoreCourseCode(TestCase):
    def test_valid_course_codes(self):
        """Test valid course code patterns"""
        self.assertEqual(restore_course_code("math111"), "MATH-111")
        self.assertEqual(restore_course_code("COSC111"), "COSC-111")
        self.assertEqual(restore_course_code("stat231"), "STAT-231")

    def test_invalid_course_codes(self):
        """Test invalid course code patterns"""
        self.assertEqual(restore_course_code("math"), "math")  # no numbers
        self.assertEqual(restore_course_code("111"), "111")  # only numbers
        self.assertEqual(restore_course_code(""), "")  # empty string


class TestCleanQuery(TestCase):
    def test_stop_words_removal(self):
        """Test removal of stop words"""
        query = "the introduction to computer science"
        expected = ["introduction", "computer", "science"]
        self.assertEqual(clean_query(query), expected)

    def test_special_terms(self):
        """Test handling of special terms"""
        query = "half MATH111 the"
        expected = ["half", "math111"]
        self.assertEqual(clean_query(query), expected)


class TestComputeSimilarityScores(TestCase):
    def test_empty_inputs(self):
        """Test empty query and information"""
        self.assertEqual(compute_similarity_scores("", []), [])
        self.assertEqual(compute_similarity_scores("query", []), [])
        self.assertEqual(compute_similarity_scores("", ["info"]), [0])

    def test_similarity_scores(self):
        """Test similarity computation"""
        query = "introduction to computer science"
        information = [
            "intro to computer science",
            "advanced mathematics",
            "computer programming basics",
        ]
        scores = compute_similarity_scores(query, information)
        self.assertEqual(len(scores), len(information))
        self.assertTrue(all(0 <= score <= 1 for score in scores))
        # First item should have highest similarity
        self.assertEqual(max(scores), scores[0])


class TestFilter(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        # Create test departments
        cls.math_dept = Department.objects.create(
            name="Mathematics and Statistics", code="MATH"
        )
        cls.cs_dept = Department.objects.create(name="Computer Science", code="COSC")

        # Create test divisions
        cls.division = Division.objects.create(name="Science")

        # Create test professors
        cls.prof = Professor.objects.create(name="John Smith")

        # Create test keywords
        cls.keyword = Keyword.objects.create(name="algorithms")

        # Create test courses
        cls.course1 = Course.objects.create(
            courseName="Introduction to Computer Science",
            courseDescription="Basic programming concepts",
            id=4170111,
        )

        code1 = CourseCode.objects.create(value="COSC-111")

        cls.course1.departments.add(cls.cs_dept)
        cls.course1.divisions.add(cls.division)
        cls.course1.professors.add(cls.prof)
        cls.course1.keywords.add(cls.keyword)
        cls.course1.courseCodes.set([code1])

        cls.course2 = Course.objects.create(
            courseName="Calculus I",
            courseDescription="Introduction to calculus",
            id=4250111,
        )

        code2 = CourseCode.objects.create(value="MATH-111")

        cls.course2.departments.add(cls.math_dept)
        cls.course2.courseCodes.set([code2])

    def test_empty_query(self):
        """Test empty search query"""
        courses = Course.objects.all()
        results = filter("", courses)
        self.assertEqual(len(results), len(courses))

    def test_department_search(self):
        """Test searching by department"""
        courses = Course.objects.all()
        results = filter("mathematics", courses)
        self.assertTrue(any(self.math_dept in c.departments.all() for c in results))

    def test_course_code_search(self):
        """Test searching by course code"""
        courses = Course.objects.all()
        results = filter("cosc111", courses)
        self.assertTrue(
            any(
                code.value == "COSC-111"
                for c in results
                for code in c.courseCodes.all()
            )
        )

    def test_professor_search(self):
        """Test searching by professor name"""
        courses = Course.objects.all()
        results = filter("smith", courses)
        self.assertTrue(any(self.prof in c.professors.all() for c in results))

    def test_keyword_search(self):
        """Test searching by keyword"""
        courses = Course.objects.all()
        results = filter("algorithms", courses)
        self.assertTrue(any(self.keyword in c.keywords.all() for c in results))

    def test_half_course_search(self):
        """Test searching for half courses"""
        courses = Course.objects.all()
        results = filter("half", courses)
        self.assertTrue(all(str(c.id)[3] == "1" for c in results))

    def test_combined_search(self):
        """Test searching with multiple terms"""
        courses = Course.objects.all()
        results = filter("computer science smith", courses)
        # Should match course1 with high score due to multiple matches
        self.assertTrue(self.course1 in results)
        # Should be first due to highest score
        self.assertEqual(results[0], self.course1)
