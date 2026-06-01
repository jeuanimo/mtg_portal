from django.urls import path
from . import views

app_name = 'inbox'

urlpatterns = [
    path('', views.email_inbox, name='email_inbox'),
    path('sent/', views.email_sent, name='email_sent'),
    path('sent/<str:uid>/', views.email_sent_detail, name='email_sent_detail'),
    path('compose/', views.email_compose, name='email_compose'),
    path('drafts/', views.email_draft_list, name='email_draft_list'),
    path('drafts/<int:draft_pk>/edit/', views.email_compose, name='email_draft_edit'),
    path('drafts/<int:pk>/delete/', views.email_draft_delete, name='email_draft_delete'),
    path('<str:uid>/delete/', views.email_delete, name='email_delete'),
    path('<str:uid>/mark-unread/', views.email_mark_unread, name='email_mark_unread'),
    path('<str:uid>/mark-important/', views.email_mark_important, name='email_mark_important'),
    path('<str:uid>/', views.email_detail, name='email_detail'),
]
