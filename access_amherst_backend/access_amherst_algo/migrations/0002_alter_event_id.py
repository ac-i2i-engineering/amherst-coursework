# Generated by Django 5.1.1 on 2024-10-17 23:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('access_amherst_algo', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='id',
            field=models.IntegerField(primary_key=True, serialize=False, unique=True),
        ),
    ]
