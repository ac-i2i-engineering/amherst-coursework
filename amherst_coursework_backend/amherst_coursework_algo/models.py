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
    Course model representing an academic course at Amherst College.

    Parameters
    ----------
    id : IntegerField, primary key
        Unique 7-digit course identifier
        Format: XYYZCZZ where:
        X: College/semester (4=Amherst Fall, 5=Amherst Spring)
        YY: Department code (00-99)
        Z: Credit flag (1=half-credit, 0=full-credit)
        CZZ: Course number (000-999)
        Example: 4140112 = Fall COSC-112

    courseLink : URLField, optional
        Direct URL to the course page on Amherst College's course catalog
        Defaults to null if not provided

    courseName : CharField
        Full title of the course as it appears in the course catalog
        Maximum length: 200 characters

    courseCodes : ManyToManyField to CourseCode
        Official course codes/numbers (e.g., "COSC-111", "MATH-271")
        Multiple codes possible for cross-listed courses

    courseDescription : TextField, optional
        Detailed description of course content, objectives, and requirements
        Can be blank

    courseMaterialsLink : URLField, optional
        URL to course materials, syllabus, or additional resources
        Defaults to null if not provided

    keywords : ManyToManyField to Keyword
        Searchable keywords/tags associated with the course content

    divisions : ManyToManyField to Division
        Academic divisions the course belongs to (e.g., "Science", "Humanities")

    departments : ManyToManyField to Department
        Academic departments offering the course

    enrollmentText : TextField
        Instructions for course enrollment and registration
        Defaults to "Contact the professor for enrollment details"

    prefForMajor : BooleanField
        Whether majors have enrollment priority
        Defaults to False

    overallCap : PositiveIntegerField
        Maximum total enrollment limit
        Defaults to 0 (no cap)

    freshmanCap : PositiveIntegerField
        Maximum number of freshmen allowed to enroll
        Defaults to 0 (no cap)

    sophomoreCap : PositiveIntegerField
        Maximum number of sophomores allowed to enroll
        Defaults to 0 (no cap)

    juniorCap : PositiveIntegerField
        Maximum number of juniors allowed to enroll
        Defaults to 0 (no cap)

    seniorCap : PositiveIntegerField
        Maximum number of seniors allowed to enroll
        Defaults to 0 (no cap)

    credits : IntegerField
        Number of credits awarded for completing the course
        Choices: 2 or 4 credits
        Defaults to 4

    prereqDescription : TextField, optional
        Text description of prerequisites and requirements
        Can be blank

    recommended_courses : ManyToManyField to Course
        Courses recommended but not required as prerequisites
        Self-referential relationship

    professor_override : BooleanField
        Whether professors can override prerequisite requirements
        Defaults to False

    placement_course : ForeignKey to Course, optional
        Reference to a placement test or course required
        Self-referential relationship

    corequisites : ManyToManyField to Course
        Courses that must be taken concurrently
        Self-referential, symmetrical relationship

    professors : ManyToManyField to Professor
        Professors teaching the course

    sections : ReverseRelation via Section
        Course sections with meeting times and locations
        One-to-many relationship from Section model

    fallOfferings : ManyToManyField to Year
        Years the course is offered in fall semester

    springOfferings : ManyToManyField to Year
        Years the course is offered in spring semester

    janOfferings : ManyToManyField to Year
        Years the course is offered in January term

    Methods
    -------
    __str__()
        Returns the course name as a string

    Examples
    --------
    >>> course = Course.objects.create(
    ...     id=4140111,
    ...     courseName="Introduction to Computer Science I",
    ...     credits=4
    ... )
    >>> course.departments.add(Department.objects.get(code="COSC"))
    >>> course.courseCodes.create(value="COSC-111")
    """

    id = models.IntegerField(
        primary_key=True,
        validators=[MinValueValidator(0), MaxValueValidator(9999999)],
        help_text="Unique 7-digit course identifier. Format: XYYZCZZ where: X: College/semester (4=Amherst Fall, 5=Amherst Spring), YY: Department code (00-99), Z: Credit flag (1=half-credit, 0=full-credit), CZZ: Course number (000-999). Example: 4140112 = Fall COSC-112",
    )
    courseLink = models.URLField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Direct URL to the course page on Amherst College's course catalog. Defaults to null if not provided.",
    )
    courseName = models.CharField(
        max_length=200,
        help_text="Full title of the course as it appears in the course catalog. Maximum length: 200 characters.",
    )
    courseCodes = models.ManyToManyField(
        "CourseCode",
        related_name="courses",
        help_text="Official course codes/numbers (e.g., 'COSC-111', 'MATH-271'). Multiple codes possible for cross-listed courses.",
    )
    courseDescription = models.TextField(
        blank=True,
        help_text="Detailed description of course content, objectives, and requirements. Can be blank.",
    )
    courseMaterialsLink = models.URLField(
        max_length=200,
        blank=True,
        null=True,
        help_text="URL to course materials, syllabus, or additional resources. Defaults to null if not provided.",
    )
    keywords = models.ManyToManyField(
        "Keyword",
        related_name="courses",
        help_text="Searchable keywords/tags associated with the course content.",
    )
    divisions = models.ManyToManyField(
        "Division",
        related_name="courses",
        help_text="Academic divisions the course belongs to (e.g., 'Science', 'Humanities').",
    )
    departments = models.ManyToManyField(
        "Department",
        related_name="courses",
        help_text="Academic departments offering the course.",
    )
    enrollmentText = models.TextField(
        default="Contact the professor for enrollment details.",
        help_text="Instructions for course enrollment and registration. Defaults to 'Contact the professor for enrollment details.'",
    )
    prefForMajor = models.BooleanField(
        default=False,
        help_text="Whether majors have enrollment priority. Defaults to False.",
    )
    overallCap = models.PositiveIntegerField(
        default=0, help_text="Maximum total enrollment limit. Defaults to 0 (no cap)."
    )
    freshmanCap = models.PositiveIntegerField(
        default=0,
        help_text="Maximum number of freshmen allowed to enroll. Defaults to 0 (no cap).",
    )
    sophomoreCap = models.PositiveIntegerField(
        default=0,
        help_text="Maximum number of sophomores allowed to enroll. Defaults to 0 (no cap).",
    )
    juniorCap = models.PositiveIntegerField(
        default=0,
        help_text="Maximum number of juniors allowed to enroll. Defaults to 0 (no cap).",
    )
    seniorCap = models.PositiveIntegerField(
        default=0,
        help_text="Maximum number of seniors allowed to enroll. Defaults to 0 (no cap).",
    )
    credits = models.IntegerField(
        default=4,
        choices=[(2, "2 credits"), (4, "4 credits")],
        help_text="Number of credits awarded for completing the course. Choices: 2 or 4 credits. Defaults to 4.",
    )
    prereqDescription = models.TextField(
        blank=True,
        help_text="Text description of prerequisites and requirements. Can be blank.",
    )
    recommended_courses = models.ManyToManyField(
        "Course",
        blank=True,
        related_name="recommended_for",
        help_text="Courses recommended but not required as prerequisites. Self-referential relationship.",
    )
    professor_override = models.BooleanField(
        default=False,
        help_text="Whether professors can override prerequisite requirements. Defaults to False.",
    )
    placement_course = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="placement_for",
        help_text="Reference to a placement test or course required. Self-referential relationship.",
    )
    corequisites = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=True,
        help_text="Courses that must be taken concurrently. Self-referential, symmetrical relationship.",
    )
    professors = models.ManyToManyField(
        "Professor", related_name="courses", help_text="Professors teaching the course."
    )
    fallOfferings = models.ManyToManyField(
        "Year",
        related_name="fOfferings",
        blank=True,
        help_text="Years the course is offered in fall semester.",
    )
    springOfferings = models.ManyToManyField(
        "Year",
        related_name="sOfferings",
        blank=True,
        help_text="Years the course is offered in spring semester.",
    )
    janOfferings = models.ManyToManyField(
        "Year",
        related_name="jOfferings",
        blank=True,
        help_text="Years the course is offered in January term.",
    )

    def clean(self):
        """Validates that year-specific enrollment caps don't exceed overall cap"""
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
    value : CharField
        The 8-9 character course code (e.g., "COSC-111", "CHEM-165L")
        Must follow department code + hyphen + number format + (optional) letter suffix
    """

    value = models.CharField(
        max_length=9,
        validators=[MinLengthValidator(8), MaxLengthValidator(9)],
        help_text="The 8-9 character course code (e.g., 'COSC-111', 'CHEM-165L'). Must follow department code + hyphen + number format.",
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
    name : CharField
        The full name of the department (e.g., "Computer Science", "Biology")
    code : CharField
        The 4-letter department code (e.g., "COSC", "BCBP")
    link : URLField
        The link to the department page on amherst.edu
    """

    name = models.CharField(
        max_length=100,
        help_text="The full name of the department (e.g., 'Computer Science', 'Biology')",
    )
    code = models.CharField(
        max_length=4,
        validators=[MinLengthValidator(4), MaxLengthValidator(4)],
        help_text="The 4-letter department code (e.g., 'COSC', 'BCBP')",
    )
    link = models.URLField(
        max_length=200, help_text="The link to the department page on amherst.edu"
    )

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
        help_text="Course this set of prerequisites is for",
    )
    courses = models.ManyToManyField(
        "Course",
        help_text="One set of courses that can be completed to satisfy prerequisites",
    )

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
    name : CharField
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
    Section model representing a specific course section with location, professor, and meeting time.

    Parameters
    ----------
    section_number: CharField
        The section number (digits with optional letter suffix)
    section_for : ForeignKey
        Course this section is for
    monday_start_time : TimeField
        Start time for Monday meeting
    monday_end_time : TimeField
        End time for Monday meeting
    tuesday_start_time : TimeField
        Start time for Tuesday meeting
    tuesday_end_time : TimeField
        End time for Tuesday meeting
    wednesday_start_time : TimeField
        Start time for Wednesday meeting
    wednesday_end_time : TimeField
        End time for Wednesday meeting
    thursday_start_time : TimeField
        Start time for Thursday meeting
    thursday_end_time : TimeField
        End time for Thursday meeting
    friday_start_time : TimeField
        Start time for Friday meeting
    friday_end_time : TimeField
        End time for Friday meeting
    saturday_start_time : TimeField
        Start time for Saturday meeting
    saturday_end_time : TimeField
        End time for Saturday meeting
    sunday_start_time : TimeField
        Start time for Sunday meeting
    sunday_end_time : TimeField
        End time for Sunday meeting
    location : CharField
        Building and room number
    professor : ForeignKey
        Professor teaching this section
    """

    section_number = models.CharField(
        validators=[
            RegexValidator(
                regex=r"^\d{2}[A-Z]?$",
                message="Section number must be 2 digits optionally followed by a capital letter",
                code="invalid_section_number",
            )
        ],
        help_text="Section number (digits or L for lab)",
        max_length=2,
        default="1",
    )
    section_for = models.ForeignKey(
        "Course",
        on_delete=models.CASCADE,
        related_name="sections",
        default=None,
    )

    monday_start_time = models.TimeField(
        null=True, help_text="Start time for Monday meeting"
    )
    monday_end_time = models.TimeField(
        null=True, help_text="End time for Monday meeting"
    )
    tuesday_start_time = models.TimeField(
        null=True, help_text="Start time for Tuesday meeting"
    )
    tuesday_end_time = models.TimeField(
        null=True, help_text="End time for Tuesday meeting"
    )
    wednesday_start_time = models.TimeField(
        null=True, help_text="Start time for Wednesday meeting"
    )
    wednesday_end_time = models.TimeField(
        null=True, help_text="End time for Wednesday meeting"
    )
    thursday_start_time = models.TimeField(
        null=True, help_text="Start time for Thursday meeting"
    )
    thursday_end_time = models.TimeField(
        null=True, help_text="End time for Thursday meeting"
    )
    friday_start_time = models.TimeField(
        null=True, help_text="Start time for Friday meeting"
    )
    friday_end_time = models.TimeField(
        null=True, help_text="End time for Friday meeting"
    )
    saturday_start_time = models.TimeField(
        null=True, help_text="Start time for Saturday meeting"
    )
    saturday_end_time = models.TimeField(
        null=True, help_text="End time for Saturday meeting"
    )
    sunday_start_time = models.TimeField(
        null=True, help_text="Start time for Sunday meeting"
    )
    sunday_end_time = models.TimeField(
        null=True, help_text="End time for Sunday meeting"
    )

    location = models.CharField(max_length=100, help_text="Building and room number")
    professor = models.ForeignKey(
        "Professor", on_delete=models.CASCADE, related_name="sections"
    )

    def clean(self):
        super().clean()

        # Check that start times are before end times for each day
        time_pairs = [
            ("monday", self.monday_start_time, self.monday_end_time),
            ("tuesday", self.tuesday_start_time, self.tuesday_end_time),
            ("wednesday", self.wednesday_start_time, self.wednesday_end_time),
            ("thursday", self.thursday_start_time, self.thursday_end_time),
            ("friday", self.friday_start_time, self.friday_end_time),
            ("saturday", self.saturday_start_time, self.saturday_end_time),
            ("sunday", self.sunday_start_time, self.sunday_end_time),
        ]

        errors = {}
        for day, start_time, end_time in time_pairs:
            if start_time and end_time:  # Only validate if both times are set
                if start_time >= end_time:
                    errors[f"{day}_start_time"] = (
                        f"{day.capitalize()} start time must be before end time"
                    )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.section_number} for {self.section_for}"

    class Meta:
        verbose_name = "Section"
        verbose_name_plural = "Sections"
        unique_together = ("section_for", "section_number")


class Year(models.Model):
    """
    Year model representing the academic year (specfic to each course).

    Parameters
    ----------
    id : IntegerField
        Unique identifier for the academic year/link combo
    year : IntegerField
        Academic year (e.g., 2021)
    link : URLField
        URL link to course catalog
    """

    id = models.AutoField(primary_key=True)
    year = models.IntegerField(
        validators=[MinValueValidator(1900)], help_text="Academic year (e.g., 2021)"
    )
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
    name: CharField
        The keyword value
    """

    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Keyword"
        verbose_name_plural = "Keywords"
        ordering = ["name"]


class Division(models.Model):
    """
    Division model representing academic divisions at Amherst College.

    Parameters
    ----------
    name : CharField
        The full name of the division (e.g., "Science & Mathematics", "Social Sciences")
    """

    name = models.CharField(
        max_length=100,
        help_text="The full name of the division (e.g., 'Science & Mathematics', 'Social Sciences')",
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Division"
        verbose_name_plural = "Divisions"
        ordering = ["name"]
