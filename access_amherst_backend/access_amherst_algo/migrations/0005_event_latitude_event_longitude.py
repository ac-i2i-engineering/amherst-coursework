# Generated by Django 5.1.1 on 2024-10-31 19:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("access_amherst_algo", "0004_event_author_email"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="latitude",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="event",
            name="longitude",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
