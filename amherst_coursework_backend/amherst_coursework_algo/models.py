from django.db import models
from django.contrib.auth.models import User
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    MinLengthValidator,
    MaxLengthValidator,
)
from django.db.models import Avg
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


class Course(models.Model):
    """
    Course model representing an academic course at Amherst College with details about the course.

    Parameters
    ----------
    id : int
        Unique 7-digit course identifier; primary key
        The first digit represents the college and semester (e.g., 4 for Amherst College Fall and 5 for Amherst College Spring)
        The second and third digits represent the department code (e.g., 00 for American Studies)
        The fourth digit is a boolean flag for whether the course is half-credit (1) or full-credit (0)
        The last three digits are the course number
        Example: 4140112 represents 4-credit COSC-112 at Amherst College in the Fall semester
    courseLink : URLField
        URL link to the course page
    courseName : str
        The full name/title of the course
    courseCodes : ManyToManyField
        Related CourseCode objects (e.g., "COSC111")
    courseDescription : TextField
        Description of the course
    courseMaterialsLink : URLField
        URL link to course materials
    keywords : ManyToManyField
        Keywords associated with the course
    divisions : ManyToManyField
        Academic divisions the course belongs to
    departments : ManyToManyField
        Related Department objects for this course
    enrollmentText : TextField
        Text describing enrollment details
    prefForMajor : bool
        Whether course has preference for majors
    overallCap : int
        Overall enrollment cap for the course
    freshmanCap : int
        Enrollment cap for freshmen
    sophomoreCap : int
        Enrollment cap for sophomores
    juniorCap : int
        Enrollment cap for juniors
    seniorCap : int
        Enrollment cap for seniors
    credits : int
        Number of course credits (2 or 4)
    prereqDescription : TextField
        Description of prerequisites
    required_courses : ManyToManyField
        Required prerequisite course sets
    recommended_courses : ManyToManyField
        Recommended prerequisite courses
    professor_override : bool
        Whether professor can override prerequisites
    placement_course : int
        Course ID for placement test course
    corequisites : ManyToManyField
        Related Course objects that are corequisites
    professors : ManyToManyField
        Related Professor objects teaching this course
    sections : ManyToManyField
        Related Section objects for meeting times/locations
    fallOfferings : ManyToManyField
        Years the course is offered in Fall semester
    springOfferings : ManyToManyField
        Years the course is offered in Spring semester
    janOfferings : ManyToManyField
        Years the course is offered in January term
    """

    id = models.IntegerField(
        primary_key=True, validators=[MinValueValidator(0), MaxValueValidator(9999999)]
    )
    courseLink = models.URLField(max_length=200, blank=True, null=True)
    courseName = models.CharField(max_length=200)
    courseCodes = models.ManyToManyField("CourseCode", related_name="courses")
    courseDescription = models.TextField(blank=True)
    courseMaterialsLink = models.URLField(max_length=200, blank=True, null=True)
    keywords = models.ManyToManyField("Keyword", related_name="courses")
    divisions = models.ManyToManyField("Division", related_name="courses")
    departments = models.ManyToManyField("Department", related_name="courses")
    enrollmentText = models.TextField(
        default="Contact the professor for enrollment details."
    )
    prefForMajor = models.BooleanField(default=False)
    overallCap = models.PositiveIntegerField(default=0)
    freshmanCap = models.PositiveIntegerField(default=0)
    sophomoreCap = models.PositiveIntegerField(default=0)
    juniorCap = models.PositiveIntegerField(default=0)
    seniorCap = models.PositiveIntegerField(default=0)

    credits = models.IntegerField(
        default=4, choices=[(2, "2 credits"), (4, "4 credits")]
    )
    prereqDescription = models.TextField(
        blank=True, help_text="Text description of prerequisites"
    )
    recommended_courses = models.ManyToManyField(
        "Course", blank=True, related_name="recommended_for"
    )
    professor_override = models.BooleanField(
        default=False, help_text="Can professor override prerequisites?"
    )
    placement_course = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="placement_for",
    )
    corequisites = models.ManyToManyField("self", blank=True, symmetrical=True)
    professors = models.ManyToManyField("Professor", related_name="courses")
    fallOfferings = models.ManyToManyField(
        "Year", related_name="fOfferings", blank=True
    )
    springOfferings = models.ManyToManyField(
        "Year", related_name="sOfferings", blank=True
    )
    janOfferings = models.ManyToManyField("Year", related_name="jOfferings", blank=True)

    def clean(self):
        """Validate that year caps don't exceed overall cap"""
        super().clean()

        if self.overallCap > 0:  # Only validate if overall cap is set
            caps = {
                "Freshman": self.freshmanCap,
                "Sophomore": self.sophomoreCap,
                "Junior": self.juniorCap,
                "Senior": self.seniorCap,
            }

            for year, cap in caps.items():
                if cap > self.overallCap:
                    raise ValidationError(
                        {
                            f"{year.lower()}Cap": f"{year} cap ({cap}) cannot exceed overall cap ({self.overallCap})"
                        }
                    )

    def __str__(self):
        return self.courseName


class CourseCode(models.Model):
    """
    CourseCode model representing course codes/abbreviations.

    Parameters
    ----------
    value : str
        The 8-9 character course code (e.g., "COSC-111", "CHEM-165L")
    """

    value = models.CharField(
        max_length=9, validators=[MinLengthValidator(8), MaxLengthValidator(9)]
    )

    def __str__(self):
        return self.value

    class Meta:
        verbose_name = "Course Code"
        verbose_name_plural = "Course Codes"


class Department(models.Model):
    """
    Department model representing academic departments at Amherst College.

    Parameters
    ----------
    name : str
        The full name of the department (e.g., "Computer Science", "Biology")
    code : str
        The 4-letter department code (e.g., "COSC", "BCBP")
    link : URLField
        The link to the department page on amherst.edu
    """

    name = models.CharField(max_length=100)
    code = models.CharField(
        max_length=4, validators=[MinLengthValidator(4), MaxLengthValidator(4)]
    )
    link = models.URLField(max_length=200)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"


class PrerequisiteSet(models.Model):
    """
    PrerequisiteSet model representing a set of prerequisites for a course.

    Parameters
    ----------
    prerequisite_for : ForeignKey
        Course this set of prerequisites is for
    courses : ManyToManyField
        One set of courses that can be completed to satisfy prerequisites
    """

    prerequisite_for = models.ForeignKey(
        "Course",
        on_delete=models.CASCADE,
        related_name="required_courses",
        default=None,
    )
    courses = models.ManyToManyField("Course")

    def __str__(self):
        return ", ".join(
            [str(course) for course in self.courses.all().select_related()]
        )

    class Meta:
        verbose_name = "Prerequisite Set"
        verbose_name_plural = "Prerequisite Sets"


class Professor(models.Model):
    """
    Professor model representing course instructors.

    Parameters
    ----------
    name : str
        Full name of the professor
    link : URLField
        URL to professor's page on amherst.edu
    """

    name = models.CharField(max_length=100, help_text="Full name of the professor")
    link = models.URLField(
        max_length=200, blank=True, null=True, help_text="Link to professor's page"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Professor"
        verbose_name_plural = "Professors"
        ordering = ["name"]


class Section(models.Model):
    """
    Section model representing a specific course meeting time.

    Parameters
    ----------
    section_number: int
        The section number
    section_for : ForeignKey
        Course this section is for
    days : str
        Days of the week the section meets
    start_time : TimeField
        Start time of the section
    end_time : TimeField
        End time of the section
    location : str
        Building and room number
    professor : ForeignKey
        Professor teaching this section
    """

    section_number = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(99)],
        help_text="Section number",
        default=1,
    )
    section_for = models.ForeignKey(
        "Course",
        on_delete=models.CASCADE,
        related_name="sections",
        default=None,
    )
    monday_start_time = models.TimeField()

    location = models.CharField(max_length=100, help_text="Building and room number")
    professor = models.ForeignKey(
        "Professor", on_delete=models.CASCADE, related_name="sections"
    )

    def clean(self):
        super().clean()
        if self.start_time >= self.end_time:
            raise ValidationError(_("End time must be after start time"))

        if len(set(self.days)) != len(self.days):
            raise ValidationError(_("Duplicate days not allowed"))

    def __str__(self):

        return f"{self.days} {self.start_time}-{self.end_time} in {self.location}"

    class Meta:
        verbose_name = "Section"
        verbose_name_plural = "Sections"
        unique_together = ("section_for", "section_number")


class Year(models.Model):
    """
    Year model representing the academic year (specfic to each course).

    Parameters
    ----------
    id : int
        Unique identifier for the academic year/link combo
    year : int
        Academic year (e.g., 2021)
    link : URLField
        URL link to course catalog
    """

    id = models.AutoField(primary_key=True)
    year = models.IntegerField(validators=[MinValueValidator(1900)])
    link = models.URLField(
        max_length=200, help_text="Link to course catalog", null=True
    )

    def __str__(self):
        return str(self.year)

    class Meta:
        verbose_name = "Year"
        verbose_name_plural = "Years"
        ordering = ["year"]


class Keyword(models.Model):
    """
    Keyword model representing keywords associated with courses.

    Parameters
    ----------
    name : str
        The keyword value
    """

    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.value

    class Meta:
        verbose_name = "Keyword"
        verbose_name_plural = "Keywords"
        ordering = ["name"]


class Division(models.Model):
    """
    Division model representing academic divisions at Amherst College.

    Parameters
    ----------
    name : str
        The full name of the division (e.g., "Science & Mathematics", "Social Sciences")
    """

    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Division"
        verbose_name_plural = "Divisions"
        ordering = ["name"]
