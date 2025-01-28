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
    department : ManyToManyField
        Related Department objects for this course
    overGuidelines : OneToOneField
        Related OverGuidelines object for handling overenrollment
    credits : int
        Number of course credits (2 or 4)
    prerequisites : OneToOneField
        Related Prerequisites object
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
        Years the course is offered in the January term
    """

    id = models.IntegerField(
        primary_key=True, validators=[MinValueValidator(0), MaxValueValidator(9999999)]
    )
    courseLink = models.URLField(max_length=200, blank=True)
    courseName = models.CharField(max_length=200)
    courseCodes = models.ManyToManyField("CourseCode")
    courseDescription = models.TextField(blank=True)
    # categories = models.ManyToManyField('Category', related_name='courses')
    department = models.ManyToManyField("Department", related_name="dept_courses")
    overGuidelines = models.OneToOneField(
        "OverGuidelines", on_delete=models.SET_NULL, null=True, blank=True
    )
    credits = models.IntegerField(
        default=4, choices=[(2, "2 credits"), (4, "4 credits")]
    )
    prerequisites = models.OneToOneField(
        "Prerequisites",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prerequisites_for",
    )
    corequisites = models.ManyToManyField("self", blank=True, symmetrical=True)
    professors = models.ManyToManyField("Professor", related_name="courses")
    sections = models.ManyToManyField("Section")
    fallOfferings = models.ManyToManyField(
        "Year", related_name="fOfferings", blank=True
    )
    springOfferings = models.ManyToManyField(
        "Year", related_name="sOfferings", blank=True
    )
    janOfferings = models.ManyToManyField("Year", related_name="jOfferings", blank=True)

    def __str__(self):
        return self.courseName


class CourseCode(models.Model):
    """
    CourseCode model representing course codes/abbreviations.

    Parameters
    ----------
    value : str
        The 7-8 character course code (e.g., "COSC111", "CHEM165L")
    """

    value = models.CharField(
        max_length=8, validators=[MinLengthValidator(7), MaxLengthValidator(8)]
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


class OverGuidelines(models.Model):
    """
    OverGuidelines model representing overenrollment instructions for a course.

    Parameters
    ----------
    myCourse : ForeignKey
        Course this overenrollment guideline is for
    text : str
        Instructions for handling overenrollment
    prefForMajor : bool
        Whether the course is preferred for majors
    overallCap : int
        Maximum total enrollment limit
    freshmanCap : int
        Enrollment cap for freshmen
    sophomoreCap : int
        Enrollment cap for sophomores
    juniorCap : int
        Enrollment cap for juniors
    seniorCap : int
        Enrollment cap for seniors
    """

    myCourse = models.ForeignKey("Course", on_delete=models.CASCADE, default=None)
    text = models.TextField()
    prefForMajor = models.BooleanField(default=False)
    overallCap = models.PositiveIntegerField(default=0)
    freshmanCap = models.PositiveIntegerField(default=0)
    sophomoreCap = models.PositiveIntegerField(default=0)
    juniorCap = models.PositiveIntegerField(default=0)
    seniorCap = models.PositiveIntegerField(default=0)

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
        return self.text

    class Meta:
        verbose_name = "Overenrollment Guidelines"
        verbose_name_plural = "Overenrollment Guidelines"


class Prerequisites(models.Model):
    """
    Prerequisites model representing course prerequisites.

    Parameters
    ----------
    description : str
        Text description of prerequisites
    required_courses : ManyToManyField
        Sets of courses where completing any single set satisfies prerequisites
    recommended_courses : ManyToManyField
        Courses that are recommended but not required
    professor_override : bool
        Whether professor can override prerequisites
    placement_course : OneToOneField
        Course that students need to place out of to satisfy prerequisites
    """

    description = models.TextField(
        blank=True, help_text="Text description of prerequisites"
    )
    required_courses = models.ManyToManyField(
        "PrerequisiteSet", blank=True, related_name="required_for"
    )
    recommended_courses = models.ManyToManyField(
        "Course", blank=True, related_name="recommended_for"
    )
    professor_override = models.BooleanField(
        default=False, help_text="Can professor override prerequisites?"
    )
    placement_course = models.OneToOneField(
        "Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="placement_for",
    )

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = "Prerequisites"
        verbose_name_plural = "Prerequisites"


class PrerequisiteSet(models.Model):
    """
    PrerequisiteSet model representing a set of prerequisites for a course.

    Parameters
    ----------
    courses : ManyToManyField
        One set of courses that can be completed to satisfy prerequisites
    """

    courses = models.ManyToManyField("Course")

    def __str__(self):
        return ", ".join([str(course) for course in self.courses])

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
    myCourse : ForeignKey
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
    myCourse = models.ForeignKey(
        "Course",
        on_delete=models.CASCADE,
        related_name="course_sections",
        default=None,
    )
    days = models.CharField(
        max_length=5,
        help_text="Days of week (e.g., MWF, TR)",
        validators=[
            RegexValidator(
                regex="^[MTWRF]+$", message="Days must be combination of M/T/W/R/F"
            )
        ],
    )
    start_time = models.TimeField(help_text="Section start time")
    end_time = models.TimeField(help_text="Section end time")
    location = models.CharField(max_length=100, help_text="Building and room number")
    professor = models.ForeignKey(
        "Professor", on_delete=models.CASCADE, related_name="sections"
    )

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError(_("End time must be after start time"))

    def __str__(self):

        return f"{self.days} {self.start_time}-{self.end_time} in {self.location}"

    class Meta:
        verbose_name = "Section"
        verbose_name_plural = "Sections"
        ordering = ["days", "start_time"]
        unique_together = ("myCourse", "section_number")


class Year(models.Model):
    """
    Year model representing the academic year (specfic to each course).

    Parameters
    ----------
    year : int
        Academic year (e.g., 2021)
    link : URLField
        URL link to course catalog
    """

    year = models.IntegerField(primary_key=True, validators=[MinValueValidator(1900)])
    link = models.URLField(max_length=200, help_text="Link to course catalog")

    def __str__(self):
        return str(self.year)

    class Meta:
        verbose_name = "Year"
        verbose_name_plural = "Years"
        ordering = ["year"]
