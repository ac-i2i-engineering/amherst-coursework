from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.home, name="home"),
    path("details/<int:course_id>/", views.course_details, name="course_details"),
]
