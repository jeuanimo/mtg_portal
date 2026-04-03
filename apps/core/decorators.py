"""
Redirect-based permission decorators for portal access checks.

These decorators redirect with a user-friendly message on access failure, which
is appropriate for views where a hard 403 would be confusing (e.g. meeting flows
that non-staff users might navigate to).  For internal portal views that should
return HTTP 403, use apps.accounts.decorators instead.
"""
from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

LOGIN_URL_NAME = 'account_login'


def staff_required(view_func):
    """Require access to internal staff workflows."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(LOGIN_URL_NAME)
        if not request.user.is_staff_user:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('public:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Require an administrative portal role."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(LOGIN_URL_NAME)
        if not request.user.is_admin_user:
            messages.error(request, 'Administrator access required.')
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return wrapper


def client_required(view_func):
    """Require a client user tied to an organization."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(LOGIN_URL_NAME)
        if not request.user.is_client_user or not request.user.organization_id:
            messages.error(request, 'Client access required.')
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return wrapper


def role_required(*roles):
    """Require one of the specified portal roles."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(LOGIN_URL_NAME)
            if not request.user.has_any_role(*roles):
                messages.error(request, 'You do not have the required role to access this page.')
                return redirect('dashboard:index')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
