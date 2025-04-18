# Generated by Django 5.1.4 on 2025-03-08 01:47

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "amherst_coursework_algo",
            "0002_alter_section_options_remove_section_days_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="section",
            name="section_number",
            field=models.CharField(
                default="1",
                help_text="Section number (digits or L for lab)",
                max_length=2,
                validators=[
                    django.core.validators.RegexValidator(
                        code="invalid_section_number",
                        message="Section number must be 1-2 digits or L",
                        regex="^(\\d{1,2}|L)$",
                    )
                ],
            ),
        ),
    ]
