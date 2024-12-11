.. Mammoth Course Compass documentation master file, created by
   sphinx-quickstart on Tue Oct 29 20:08:27 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Mammoth Course  Compass's Documentation!
====================================================

This project is made possible through i2i (Ideas 2 Innovation) initiative, a student-led venture accelerator, at Amherst College.

Overview
========

Mammoth Course Compass aims to provide an anonymous way for Amherst students to review courses and professors, and simultaneously read reviews to inform course scheduling decisions.

Getting Started
===============

To clone the app, run in terminal:

.. code-block:: bash

   git clone https://github.com/ac-i2i-engineering/mammoth-course-compass.git
   cd mammoth-course-compass

Set up a virtual environment and activate it to "containerize" the dependencies:

.. code-block:: bash

   python3 -m venv env
   source env/bin/activate

To run the app locally, run:

.. code-block:: bash

   pip install -r requirements.txt
   cd mammoth_course_compass_backend
   python manage.py makemigrations
   python manage.py migrate
   python manage.py runserver

Contents
========

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   course_model
   course_rating_model


Additional Resources
====================

For more information on how to contribute, report issues, or request features, please refer to our [GitHub repository](https://github.com/ac-i2i-engineering/access-amherst).
