from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserUpdateForm, UserProfileForm, NotificationSettingsForm

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
