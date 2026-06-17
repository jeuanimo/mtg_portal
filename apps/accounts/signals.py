from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserProfile


def _derive_name_from_email(user):
    """Derive a friendly first/last name when signup provides email only."""
    if user.first_name or user.last_name:
        return user.first_name or 'Client', user.last_name or 'Contact'

    local_part = (user.email or '').split('@')[0].replace('.', ' ').replace('_', ' ').strip()
    if not local_part:
        return 'Client', 'Contact'

    pieces = [piece for piece in local_part.split(' ') if piece]
    if len(pieces) == 1:
        return pieces[0].title(), 'Contact'
    return pieces[0].title(), ' '.join(piece.title() for piece in pieces[1:])


def _company_name_from_user_and_request(user, latest_request):
    if latest_request and latest_request.company:
        return latest_request.company.strip()
    if user.company:
        return user.company.strip()
    return ''


def _get_or_create_signup_organization(user, email, latest_request, organization_model):
    organization = user.organization
    company_name = _company_name_from_user_and_request(user, latest_request)
    if organization or not company_name:
        return organization

    organization, _ = organization_model.objects.get_or_create(
        name=company_name,
        defaults={
            'email': email,
            'phone': latest_request.phone if latest_request and latest_request.phone else user.phone,
        },
    )
    return organization


def _get_or_create_signup_contact(user, email, organization, latest_request, contact_model):
    contact = contact_model.objects.filter(email__iexact=email).select_related('organization').first()
    if not contact:
        first_name, last_name = _derive_name_from_email(user)
        return contact_model.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=user.phone or (latest_request.phone if latest_request else ''),
            organization=organization,
            user=user,
            is_primary=True,
        )

    updates = []
    if not contact.user_id:
        contact.user = user
        updates.append('user')
    if not contact.organization_id and organization:
        contact.organization = organization
        updates.append('organization')
    if not contact.phone and user.phone:
        contact.phone = user.phone
        updates.append('phone')
    if updates:
        contact.save(update_fields=updates)
    return contact


def _sync_user_role_and_org(user, organization, email, service_request_model):
    user_updates = []
    if not user.organization_id and organization:
        user.organization = organization
        user_updates.append('organization')

    request_converted = service_request_model.objects.filter(
        email__iexact=email,
        status=service_request_model.Status.CONVERTED,
    ).exists()
    if request_converted and user.role == User.Role.PROSPECT:
        user.role = User.Role.CLIENT
        user_updates.append('role')

    if user_updates:
        user.save(update_fields=user_updates)


def _ensure_signup_prospect_lead(user, email, contact, organization, lead_model):
    if user.role != User.Role.PROSPECT:
        return

    lead_title = f'Website Signup - {email}'
    lead_exists = lead_model.objects.filter(
        contact=contact,
        title=lead_title,
        source=lead_model.Source.WEBSITE,
    ).exists()
    if lead_exists:
        return

    lead_model.objects.create(
        title=lead_title,
        contact=contact,
        organization=organization,
        source=lead_model.Source.WEBSITE,
        status=lead_model.Status.NEW,
        priority=lead_model.Priority.MEDIUM,
        notes='Auto-created from account signup flow.',
    )


def _sync_signup_to_crm(user):
    """Mirror signup data into CRM so account and intake workflows stay aligned."""
    # Internal users should not become CRM prospects/clients.
    if user.is_staff or user.is_superuser:
        return

    from apps.crm.models import Organization, Contact, Lead
    from apps.public.models import ServiceRequest

    email = (user.email or '').strip()
    if not email:
        return

    latest_request = ServiceRequest.objects.filter(email__iexact=email).order_by('-created_at').first()

    organization = _get_or_create_signup_organization(user, email, latest_request, Organization)
    contact = _get_or_create_signup_contact(user, email, organization, latest_request, Contact)

    if not organization and contact.organization_id:
        organization = contact.organization

    _sync_user_role_and_org(user, organization, email, ServiceRequest)
    _ensure_signup_prospect_lead(user, email, contact, organization, Lead)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create user profile when a new user is created."""
    if created:
        UserProfile.objects.create(user=instance)
        _sync_signup_to_crm(instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save user profile when user is saved."""
    if hasattr(instance, 'profile'):
        instance.profile.save()
