from django.urls import path
from . import views

app_name = 'status'

urlpatterns = [
    path('', views.index, name='index'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/login/', views.dashboard_login, name='dashboard_login'),
    path('dashboard/logout/', views.dashboard_logout, name='dashboard_logout'),
    path('dashboard/incident/new/', views.dashboard_incident_create, name='dashboard_incident_create'),
    path('dashboard/incident/<int:pk>/', views.dashboard_incident_detail, name='dashboard_incident_detail'),
    path('dashboard/service/<int:pk>/status/', views.dashboard_service_status, name='dashboard_service_status'),
]
