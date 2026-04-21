"""
Admin URL routing for Phase-1
"""

from django.urls import path
from django.views.generic import RedirectView
from . import views_admin

urlpatterns = [
    path('', views_admin.admin_dashboard, name='admin_dashboard'),
    path('users/', views_admin.manage_users, name='admin_manage_users'),
    path('reports/', views_admin.reports, name='admin_reports'),
    path('analytics-data/', views_admin.admin_analytics_data, name='admin_analytics'),
    # Redirect removed "Manage Expenses" URL to admin dashboard
    path('expenses/', RedirectView.as_view(pattern_name='admin_dashboard', permanent=False)),
]
