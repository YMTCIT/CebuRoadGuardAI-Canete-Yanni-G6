from django.urls import path

from . import views

app_name = "violations"
urlpatterns = [
    path("vehicles/", views.vehicle_list, name="vehicle_list"),
    path("vehicles/add/", views.vehicle_create, name="vehicle_create"),
    path("vehicles/<int:pk>/", views.vehicle_detail, name="vehicle_detail"),
    path("vehicles/<int:pk>/edit/", views.vehicle_edit, name="vehicle_edit"),
    path("vehicles/<int:pk>/delete/", views.vehicle_delete, name="vehicle_delete"),
    path("incidents/", views.incident_list, name="incident_list"),
    path("incidents/add/", views.incident_create, name="incident_create"),
    path("incidents/simulate/", views.incident_simulate, name="incident_simulate"),
    path("incidents/<int:pk>/", views.incident_detail, name="incident_detail"),
    path("incidents/<int:pk>/edit/", views.incident_edit, name="incident_edit"),
    path("incidents/<int:pk>/delete/", views.incident_delete, name="incident_delete"),
]
