# Generated by Django 5.1.4 on 2025-02-09 04:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "amherst_coursework_algo",
            "0004_remove_course_sections_alter_course_courselink_and_more",
        ),
    ]

    operations = [
        migrations.RenameField(
            model_name="course",
            old_name="description",
            new_name="prereqDescription",
        ),
    ]
