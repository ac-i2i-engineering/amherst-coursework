# Generated by Django 5.1.4 on 2025-02-09 20:14

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CourseCode",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "value",
                    models.CharField(
                        max_length=9,
                        validators=[
                            django.core.validators.MinLengthValidator(8),
                            django.core.validators.MaxLengthValidator(9),
                        ],
                    ),
                ),
            ],
            options={
                "verbose_name": "Course Code",
                "verbose_name_plural": "Course Codes",
            },
        ),
        migrations.CreateModel(
            name="Department",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                (
                    "code",
                    models.CharField(
                        max_length=4,
                        validators=[
                            django.core.validators.MinLengthValidator(4),
                            django.core.validators.MaxLengthValidator(4),
                        ],
                    ),
                ),
                ("link", models.URLField()),
            ],
            options={
                "verbose_name": "Department",
                "verbose_name_plural": "Departments",
            },
        ),
        migrations.CreateModel(
            name="Division",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
            ],
            options={
                "verbose_name": "Division",
                "verbose_name_plural": "Divisions",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Keyword",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, unique=True)),
            ],
            options={
                "verbose_name": "Keyword",
                "verbose_name_plural": "Keywords",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Professor",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Full name of the professor", max_length=100
                    ),
                ),
                (
                    "link",
                    models.URLField(
                        blank=True, help_text="Link to professor's page", null=True
                    ),
                ),
            ],
            options={
                "verbose_name": "Professor",
                "verbose_name_plural": "Professors",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Year",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "year",
                    models.IntegerField(
                        validators=[django.core.validators.MinValueValidator(1900)]
                    ),
                ),
                (
                    "link",
                    models.URLField(help_text="Link to course catalog", null=True),
                ),
            ],
            options={
                "verbose_name": "Year",
                "verbose_name_plural": "Years",
                "ordering": ["year"],
            },
        ),
        migrations.CreateModel(
            name="Course",
            fields=[
                (
                    "id",
                    models.IntegerField(
                        primary_key=True,
                        serialize=False,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(9999999),
                        ],
                    ),
                ),
                ("courseLink", models.URLField(blank=True, null=True)),
                ("courseName", models.CharField(max_length=200)),
                ("courseDescription", models.TextField(blank=True)),
                ("courseMaterialsLink", models.URLField(blank=True, null=True)),
                (
                    "enrollmentText",
                    models.TextField(
                        default="Contact the professor for enrollment details."
                    ),
                ),
                ("prefForMajor", models.BooleanField(default=False)),
                ("overallCap", models.PositiveIntegerField(default=0)),
                ("freshmanCap", models.PositiveIntegerField(default=0)),
                ("sophomoreCap", models.PositiveIntegerField(default=0)),
                ("juniorCap", models.PositiveIntegerField(default=0)),
                ("seniorCap", models.PositiveIntegerField(default=0)),
                (
                    "credits",
                    models.IntegerField(
                        choices=[(2, "2 credits"), (4, "4 credits")], default=4
                    ),
                ),
                (
                    "prereqDescription",
                    models.TextField(
                        blank=True, help_text="Text description of prerequisites"
                    ),
                ),
                (
                    "professor_override",
                    models.BooleanField(
                        default=False, help_text="Can professor override prerequisites?"
                    ),
                ),
                (
                    "corequisites",
                    models.ManyToManyField(
                        blank=True, to="amherst_coursework_algo.course"
                    ),
                ),
                (
                    "placement_course",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="placement_for",
                        to="amherst_coursework_algo.course",
                    ),
                ),
                (
                    "recommended_courses",
                    models.ManyToManyField(
                        blank=True,
                        related_name="recommended_for",
                        to="amherst_coursework_algo.course",
                    ),
                ),
                (
                    "courseCodes",
                    models.ManyToManyField(
                        related_name="courses", to="amherst_coursework_algo.coursecode"
                    ),
                ),
                (
                    "departments",
                    models.ManyToManyField(
                        related_name="courses", to="amherst_coursework_algo.department"
                    ),
                ),
                (
                    "divisions",
                    models.ManyToManyField(
                        related_name="courses", to="amherst_coursework_algo.division"
                    ),
                ),
                (
                    "keywords",
                    models.ManyToManyField(
                        related_name="courses", to="amherst_coursework_algo.keyword"
                    ),
                ),
                (
                    "professors",
                    models.ManyToManyField(
                        related_name="courses", to="amherst_coursework_algo.professor"
                    ),
                ),
                (
                    "fallOfferings",
                    models.ManyToManyField(
                        blank=True,
                        related_name="fOfferings",
                        to="amherst_coursework_algo.year",
                    ),
                ),
                (
                    "janOfferings",
                    models.ManyToManyField(
                        blank=True,
                        related_name="jOfferings",
                        to="amherst_coursework_algo.year",
                    ),
                ),
                (
                    "springOfferings",
                    models.ManyToManyField(
                        blank=True,
                        related_name="sOfferings",
                        to="amherst_coursework_algo.year",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PrerequisiteSet",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "courses",
                    models.ManyToManyField(to="amherst_coursework_algo.course"),
                ),
                (
                    "prerequisite_for",
                    models.ForeignKey(
                        default=None,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="required_courses",
                        to="amherst_coursework_algo.course",
                    ),
                ),
            ],
            options={
                "verbose_name": "Prerequisite Set",
                "verbose_name_plural": "Prerequisite Sets",
            },
        ),
        migrations.CreateModel(
            name="Section",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "section_number",
                    models.IntegerField(
                        default=1,
                        help_text="Section number",
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(99),
                        ],
                    ),
                ),
                (
                    "days",
                    models.CharField(
                        help_text="Days of week (e.g., MWF, TR)",
                        max_length=5,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Days must be combination of M/T/W/R/F",
                                regex="^[MTWRF]+$",
                            )
                        ],
                    ),
                ),
                ("start_time", models.TimeField(help_text="Section start time")),
                ("end_time", models.TimeField(help_text="Section end time")),
                (
                    "location",
                    models.CharField(
                        help_text="Building and room number", max_length=100
                    ),
                ),
                (
                    "professor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sections",
                        to="amherst_coursework_algo.professor",
                    ),
                ),
                (
                    "section_for",
                    models.ForeignKey(
                        default=None,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sections",
                        to="amherst_coursework_algo.course",
                    ),
                ),
            ],
            options={
                "verbose_name": "Section",
                "verbose_name_plural": "Sections",
                "ordering": ["days", "start_time"],
                "unique_together": {("section_for", "section_number")},
            },
        ),
    ]
