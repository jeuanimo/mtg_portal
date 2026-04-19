from django.urls import path

from . import views

app_name = 'automations'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Campaigns
    path('campaigns/', views.campaign_list, name='campaign_list'),
    path('campaigns/create/', views.campaign_create, name='campaign_create'),
    path('campaigns/<int:pk>/', views.campaign_detail, name='campaign_detail'),
    path('campaigns/<int:pk>/edit/', views.campaign_edit, name='campaign_edit'),
    path('campaigns/<int:campaign_pk>/metrics/add/', views.metric_add, name='metric_add'),

    # Agents
    path('agents/', views.agent_list, name='agent_list'),
    path('agents/create/', views.agent_create, name='agent_create'),
    path('agents/<int:pk>/edit/', views.agent_edit, name='agent_edit'),

    # Approval Queue
    path('approval/', views.approval_queue, name='approval_queue'),

    # Tasks
    path('tasks/<int:pk>/', views.task_detail, name='task_detail'),
    path('tasks/<int:pk>/review/', views.task_review, name='task_review'),
]
