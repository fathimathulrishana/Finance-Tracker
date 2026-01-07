"""
Admin URL routing for Phase-1
"""

from django.urls import path
from . import views_admin

urlpatterns = [
    path('', views_admin.admin_dashboard, name='admin_dashboard'),
    path('users/', views_admin.manage_users, name='admin_manage_users'),
    path('expenses/', views_admin.manage_expenses, name='admin_manage_expenses'),
    path('reports/', views_admin.reports, name='admin_reports'),
]
