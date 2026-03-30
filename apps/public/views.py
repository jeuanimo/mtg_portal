from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Service, ServiceCategory, ServiceRequest, Testimonial
from .forms import ContactForm, ConsultationRequestForm


def home(request):
    """Public homepage."""
    services = Service.objects.filter(is_active=True)[:6]
    testimonials = Testimonial.objects.filter(is_active=True, is_featured=True)[:3]
    categories = ServiceCategory.objects.filter(is_active=True)[:4]
    
    context = {
        'services': services,
        'testimonials': testimonials,
        'categories': categories,
    }
    return render(request, 'public/home.html', context)


def services(request):
    """Services page."""
    services = Service.objects.filter(is_active=True).select_related('category')
    categories = ServiceCategory.objects.filter(is_active=True)
    return render(request, 'public/services.html', {
        'services': services,
        'categories': categories,
    })


def service_detail(request, slug):
    """Individual service detail page."""
    service = get_object_or_404(Service, slug=slug, is_active=True)
    related_services = Service.objects.filter(
        category=service.category, is_active=True
    ).exclude(pk=service.pk)[:3]
    return render(request, 'public/service_detail.html', {
        'service': service,
        'related_services': related_services,
    })


def about(request):
    """About us page."""
    testimonials = Testimonial.objects.filter(is_active=True)[:6]
    return render(request, 'public/about.html', {'testimonials': testimonials})


def industries(request):
    """Industries served page."""
    categories = ServiceCategory.objects.filter(is_active=True)
    return render(request, 'public/industries.html', {'categories': categories})


def consultation_request(request):
    """Request consultation form."""
    if request.method == 'POST':
        form = ConsultationRequestForm(request.POST)
        if form.is_valid():
            service_request = form.save(commit=False)
            # Capture metadata
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                service_request.ip_address = x_forwarded_for.split(',')[0]
            else:
                service_request.ip_address = request.META.get('REMOTE_ADDR', '')
            service_request.save()
            form.save_m2m()  # Save services many-to-many
            
            messages.success(
                request, 
                'Thank you for your consultation request! '
                'Our team will contact you within 24 hours.'
            )
            return redirect('public:consultation_success')
    else:
        form = ConsultationRequestForm()
    
    services = Service.objects.filter(is_active=True)
    return render(request, 'public/consultation_request.html', {
        'form': form,
        'services': services,
    })


def consultation_success(request):
    """Consultation request success page."""
    return render(request, 'public/consultation_success.html')


def contact(request):
    """Contact page with form."""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)
            # Capture IP and user agent
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                submission.ip_address = x_forwarded_for.split(',')[0]
            else:
                submission.ip_address = request.META.get('REMOTE_ADDR')
            submission.user_agent = request.META.get('HTTP_USER_AGENT', '')
            submission.save()
            
            messages.success(request, 'Thank you for your message! We\'ll get back to you soon.')
            return redirect('public:contact')
    else:
        form = ContactForm()
    
    return render(request, 'public/contact.html', {'form': form})


def blog_placeholder(request):
    """Blog placeholder page."""
    return render(request, 'public/blog.html')


def privacy_policy(request):
    """Privacy policy page."""
    return render(request, 'public/privacy.html')


def terms_of_service(request):
    """Terms of service page."""
    return render(request, 'public/terms.html')
