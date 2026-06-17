from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserUpdateForm, UserProfileForm, NotificationSettingsForm, UserAdminEditForm
from .decorators import staff_required, admin_required

# URL name constants
DASHBOARD_INDEX_URL = 'dashboard:index'
INVOICING_LIST_URL = 'invoicing:invoice_list'
PROFILE_URL = 'accounts:profile'
PROFILE_EDIT_URL = 'accounts:profile_edit'


@login_required
def after_login_redirect(request):
    """Redirect users to appropriate dashboard based on their role."""
    user = request.user
    
    # Super Admin and Finance Admin go to main dashboard
    if user.is_admin_user:
        return redirect(DASHBOARD_INDEX_URL)
    
    # Finance users go to invoicing
    if user.is_finance_user:
        return redirect(INVOICING_LIST_URL)
    
    # Staff and Consultants to staff dashboard
    if user.is_staff_user:
        return redirect(DASHBOARD_INDEX_URL)
    
    # Clients go to client dashboard
    if user.is_client_user:
        return redirect(DASHBOARD_INDEX_URL)
    
    # Prospects should complete their profile
    if user.is_prospect_user:
        messages.info(request, 'Please complete your profile to get started.')
        return redirect(PROFILE_EDIT_URL)
    
    # Default fallback
    return redirect(DASHBOARD_INDEX_URL)


@login_required
def profile_view(request):
    """Display user profile page."""
    context = {
        'user': request.user,
        'can_view_crm': request.user.can_view_crm(),
        'can_view_finances': request.user.can_view_finances(),
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit(request):
    """Edit user profile information."""
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect(PROFILE_URL)
    else:
        form = UserUpdateForm(instance=request.user)
    
    return render(request, 'accounts/profile_edit.html', {'form': form})


@login_required
def profile_address(request):
    """Edit user address information."""
    profile = request.user.profile
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your address has been updated.')
            return redirect(PROFILE_URL)
    else:
        form = UserProfileForm(instance=profile)
    
    return render(request, 'accounts/profile_address.html', {'form': form})


@login_required
def notification_settings(request):
    """Edit notification preferences."""
    if request.method == 'POST':
        form = NotificationSettingsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Notification settings updated.')
            return redirect('accounts:profile')
    else:
        form = NotificationSettingsForm(instance=request.user)
    
    return render(request, 'accounts/notification_settings.html', {'form': form})


# ---------------------------------------------------------------------------
# Staff / Admin – portal-native user management (replaces Django admin links)
# ---------------------------------------------------------------------------


@staff_required
def user_list(request):
    """Paginated, filterable list of all portal users."""
    from django.core.paginator import Paginator
    from .models import User as UserModel

    role_filter = request.GET.get('role', '')
    search = request.GET.get('q', '').strip()

    users_qs = UserModel.objects.select_related('organization').order_by('-created_at')

    if role_filter:
        users_qs = users_qs.filter(role=role_filter)

    if search:
        from django.db.models import Q
        users_qs = users_qs.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )

    paginator = Paginator(users_qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'role_filter': role_filter,
        'search': search,
        'role_choices': UserModel.Role.choices,
    }
    return render(request, 'accounts/user_list.html', context)


@staff_required
def user_detail(request, pk):
    """Read-only user detail with CRM links."""
    from .models import User as UserModel

    portal_user = get_object_or_404(UserModel, pk=pk)

    # Try to find linked CRM contact
    crm_contact = None
    try:
        from apps.crm.models import Contact
        crm_contact = Contact.objects.filter(email=portal_user.email).first()
    except Exception:
        pass

    context = {
        'portal_user': portal_user,
        'crm_contact': crm_contact,
        'can_edit': request.user.can_manage_users(),
    }
    return render(request, 'accounts/user_detail.html', context)


@admin_required
def user_edit(request, pk):
    """Admin-only: edit a portal user's role, org and basic info."""
    from .models import User as UserModel

    portal_user = get_object_or_404(UserModel, pk=pk)

    if request.method == 'POST':
        form = UserAdminEditForm(request.POST, instance=portal_user)
        if form.is_valid():
            form.save()
            messages.success(request, f'User {portal_user.email} has been updated.')
            return redirect('accounts:user_detail', pk=portal_user.pk)
    else:
        form = UserAdminEditForm(instance=portal_user)

    context = {
        'form': form,
        'portal_user': portal_user,
    }
    return render(request, 'accounts/user_edit.html', context)
