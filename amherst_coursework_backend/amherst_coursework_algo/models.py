from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg

class Course(models.Model):
    """
    Course model representing an academic course at Amherst College with details about the course. 
    This class stores course information and provides methods for retrieving rating data.

    Parameters
    ----------
    code : str
        The 8-character course code identifier (e.g., "COSC111")
    title : str  
        The full title of the course
    description : str
        A detailed description of the course content
    department : str
        The 4-letter department code (e.g., "COSC", "BCBP")
    professor : str
        Professor of the course
    keywords : str, optional
        Course keywords used for content-based filtering
    prerequisites : ManyToManyField
        Related Course objects that are prerequisites for this course
    corequisites : ManyToManyField
        Related Course objects that is a corequisite for this course

    Methods
    -------
    __str__()
        Returns a string representation of the course (code and title)
    """

    code = models.CharField(max_length=8, validators=[MinValueValidator(8)])  # e.g., "COSC-111"
    title = models.CharField(max_length=200)
    description = models.TextField()
    department = models.CharField(max_length=4, validators=[MinValueValidator(4)]) # Use 4-letter department code, e.g., "COSC", "BCBP"
    professor = models.CharField(max_length=100)
    keywords = models.TextField(blank=True)  # store course keywords
    prerequisites = models.ManyToManyField('self', blank=True)
    corequisites = models.ManyToManyField('self', blank=True)

    def __str__(self):
        return f"{self.code}: {self.title}"
