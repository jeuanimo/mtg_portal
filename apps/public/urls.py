from django.urls import path
from . import views

app_name = 'public'

urlpatterns = [
    path('', views.home, name='home'),
    path('services/', views.services, name='services'),
    path('services/<slug:slug>/', views.service_detail, name='service_detail'),
    path('about/', views.about, name='about'),
    path('industries/', views.industries, name='industries'),
    path('consultation/', views.consultation_request, name='consultation'),
    path('consultation/success/', views.consultation_success, name='consultation_success'),
    path('contact/', views.contact, name='contact'),
    path('blog/', views.blog_placeholder, name='blog'),
    path('privacy/', views.privacy_policy, name='privacy'),
    path('terms/', views.terms_of_service, name='terms'),
]
