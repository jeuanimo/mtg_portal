from django.urls import path
from . import views

app_name = 'invoicing'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.invoice_dashboard, name='dashboard'),
    
    # Invoices
    path('', views.invoice_list, name='invoice_list'),
    path('create/', views.invoice_create, name='invoice_create'),
    path('quick/', views.quick_invoice, name='quick_invoice'),
    path('<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('<int:pk>/edit/', views.invoice_edit, name='invoice_edit'),
    path('<int:pk>/send/', views.invoice_send, name='invoice_send'),
    path('<int:pk>/void/', views.invoice_void, name='invoice_void'),
    path('<int:pk>/duplicate/', views.invoice_duplicate, name='invoice_duplicate'),
    path('<int:pk>/email/', views.invoice_email, name='invoice_email'),
    path('<int:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('<int:pk>/view/<str:token>/', views.invoice_view, name='invoice_view'),
    
    # Payments
    path('payments/', views.payment_list, name='payment_list'),
    path('<int:pk>/payment/', views.payment_record, name='payment_record'),
    path('<int:pk>/pay/', views.invoice_pay, name='invoice_pay'),
    path('<int:pk>/payment-success/', views.payment_success, name='payment_success'),
    
    # Recurring invoices
    path('recurring/', views.recurring_invoice_list, name='recurring_list'),
    path('recurring/create/', views.recurring_invoice_create, name='recurring_create'),
    path('recurring/<int:pk>/edit/', views.recurring_invoice_edit, name='recurring_edit'),
    path('recurring/<int:pk>/toggle/', views.recurring_invoice_toggle, name='recurring_toggle'),
    
    # Stripe webhook
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
    
    # HTMX endpoints
    path('api/contacts/', views.get_organization_contacts, name='get_organization_contacts'),
]
