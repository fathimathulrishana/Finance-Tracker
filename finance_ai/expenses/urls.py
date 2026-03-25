from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),

    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.add_expense, name='add_expense'),
    path('expenses/<int:pk>/edit/', views.edit_expense, name='edit_expense'),
    path('expenses/<int:pk>/delete/', views.delete_expense, name='delete_expense'),
    path('expenses/download/csv/', views.download_expenses_csv, name='download_csv'),
    path('expenses/download/pdf/', views.download_expenses_pdf, name='download_pdf'),

    path('income/', views.income_list, name='income_list'),
    path('income/add/', views.add_income, name='add_income'),
    path('income/<int:pk>/edit/', views.edit_income, name='edit_income'),
    path('income/<int:pk>/delete/', views.delete_income, name='delete_income'),

    path('saving-goals/', views.goals_dashboard, name='goals_dashboard'),
    path('saving-goals/add/', views.add_saving_goal, name='add_saving_goal'),
    path('saving-goals/<int:pk>/edit/', views.edit_saving_goal, name='edit_saving_goal'),
    path('saving-goals/<int:pk>/delete/', views.delete_saving_goal, name='delete_saving_goal'),
    path('saving-goals/deposit/<int:pk>/', views.deposit_saving_goal, name='deposit_saving_goal'),
]
