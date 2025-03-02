from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.home, name="home"),
    path("details/<int:course_id>/", views.course_details, name="course_details"),
    path("cart-courses/", views.get_cart_courses, name="cart_courses"),
    path('api/course/<int:course_id>/', views.get_course_by_id, name='get_course_by_id'),

]
