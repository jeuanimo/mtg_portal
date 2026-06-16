from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.crm.models import Organization, Contact
from apps.tickets.models import ConsultingProject
from .models import Service, ServiceCategory, Testimonial
from .forms import ContactForm, ConsultationRequestForm


def _get_client_ip(request):
    """Return the best-effort client IP address from the current request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR', '')


def _split_name(full_name):
    """Split a full name into first/last names with sensible fallbacks."""
    cleaned = (full_name or '').strip()
    if not cleaned:
        return 'Client', 'Contact'
    parts = cleaned.split()
    if len(parts) == 1:
        return parts[0], 'Contact'
    return parts[0], ' '.join(parts[1:])


def _map_service_to_project_type(service):
    """Map public service selections to consulting project type."""
    haystack = ' '.join([
        service.title or '',
        service.slug or '',
        service.short_description or '',
    ]).lower()
    mapping = [
        (('web', 'website', 'app', 'software', 'frontend', 'development'),
         ConsultingProject.ProjectType.DEVELOPMENT),
        (('security', 'assessment', 'audit', 'compliance'),
         ConsultingProject.ProjectType.ASSESSMENT),
        (('migrate', 'migration', 'upgrade', 'modernization'),
         ConsultingProject.ProjectType.MIGRATION),
        (('implement', 'deployment', 'rollout', 'integration'),
         ConsultingProject.ProjectType.IMPLEMENTATION),
        (('support', 'helpdesk', 'managed', 'monitoring'),
         ConsultingProject.ProjectType.SUPPORT),
        (('training', 'workshop', 'coaching'),
         ConsultingProject.ProjectType.TRAINING),
        (('consult', 'strategy', 'advisory'),
         ConsultingProject.ProjectType.CONSULTING),
    ]
    for keywords, project_type in mapping:
        if any(keyword in haystack for keyword in keywords):
            return project_type
    return ConsultingProject.ProjectType.OTHER


def _build_intake_payload(form):
    """Build intake payload from consultation form for project intake_responses."""
    fields = [
        'budget_range', 'timeline', 'description', 'preferred_date', 'preferred_time',
        'website_type', 'target_audience', 'ui_style', 'inspiration_url',
        'preferred_color_scheme', 'avoid_colors', 'must_have_features',
        'nice_to_have_features', 'content_ready', 'accessibility_requirements',
        'responsive_priority',
    ]
    payload = {}
    for field in fields:
        value = form.cleaned_data.get(field)
        payload[field] = value.isoformat() if hasattr(value, 'isoformat') else value
    return payload


def _get_or_create_organization(service_request):
    """Find or create the organization for a consultation request."""
    organization_name = service_request.company.strip() if service_request.company else ''
    if not organization_name:
        organization_name = f"{service_request.name} Organization"

    organization, _ = Organization.objects.get_or_create(
        name=organization_name,
        defaults={
            'email': service_request.email,
            'phone': service_request.phone,
        },
    )
    return organization


def _update_contact_if_needed(contact, first_name, last_name, phone):
    """Update existing contact only for missing core fields."""
    updated = False
    if not contact.first_name:
        contact.first_name = first_name
        updated = True
    if not contact.last_name:
        contact.last_name = last_name
        updated = True
    if not contact.phone and phone:
        contact.phone = phone
        updated = True
    if updated:
        contact.save(update_fields=['first_name', 'last_name', 'phone'])


def _get_or_create_contact(service_request, organization):
    """Find or create the primary contact for a consultation request."""
    first_name, last_name = _split_name(service_request.name)
    contact, created = Contact.objects.get_or_create(
        organization=organization,
        email=service_request.email,
        defaults={
            'first_name': first_name,
            'last_name': last_name,
            'phone': service_request.phone,
            'is_primary': True,
        },
    )
    if not created:
        _update_contact_if_needed(contact, first_name, last_name, service_request.phone)
    return contact


def _create_project_from_service_request(service_request, form, organization, contact):
    """Create a consulting project and mark the service request as converted."""
    intake_payload = _build_intake_payload(form)
    intake_payload['selected_service'] = {
        'id': service_request.service_id,
        'title': service_request.service.title if service_request.service else '',
        'slug': service_request.service.slug if service_request.service else '',
    }

    project_name = f"{service_request.service.title} - {organization.name}"
    project_description = (
        f"Created from public consultation request.\n\n"
        f"Client summary: {service_request.description}"
    )

    ConsultingProject.objects.create(
        name=project_name[:200],
        description=project_description,
        project_type=_map_service_to_project_type(service_request.service),
        organization=organization,
        primary_contact=contact,
        intake_responses=intake_payload,
    )

    service_request.status = service_request.Status.CONVERTED
    service_request.internal_notes = (
        f"Auto-converted to project from consultation form for service: "
        f"{service_request.service.title if service_request.service else 'unspecified'}"
    )
    service_request.save(update_fields=['status', 'internal_notes'])


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
            service_request.ip_address = _get_client_ip(request)
            if not service_request.source:
                service_request.source = 'public_consultation'
            service_request.save()

            organization = _get_or_create_organization(service_request)
            contact = _get_or_create_contact(service_request, organization)
            _create_project_from_service_request(service_request, form, organization, contact)

            messages.success(
                request,
                'Thank you for your consultation request! '
                'We created your project intake record and our team will contact you within 24 hours.'
            )
            return redirect('public:consultation_success')
    else:
        form = ConsultationRequestForm()

    return render(request, 'public/consultation_request.html', {'form': form})


def consultation_success(request):
    """Consultation request success page."""
    return render(request, 'public/consultation_success.html')


def contact(request):
    """Contact page with form."""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.ip_address = _get_client_ip(request)
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
