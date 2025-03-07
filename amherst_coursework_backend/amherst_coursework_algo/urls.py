from django.urls import path
from . import views, masked_filters

app_name = "catalog"

urlpatterns = [
    path("", views.home, name="home"),
    path("details/<int:course_id>/", views.course_details, name="course_details"),
    path("cart-courses/", views.get_cart_courses, name="cart_courses"),
    path("api/masked_filter/", masked_filters.filter, name="filter_courses"),
]
