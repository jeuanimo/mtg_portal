"""
Permission decorators and mixins for role-based access control.
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*roles):
    """
    Decorator that checks if user has one of the specified roles.
    Usage: @role_required('super_admin', 'staff')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.role in roles or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied("You don't have permission to access this page.")
        return wrapper
    return decorator


def staff_required(view_func):
    """Decorator requiring staff role or higher."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff_user:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("Staff access required.")
    return wrapper


def admin_required(view_func):
    """Decorator requiring admin role."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_admin_user:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("Administrator access required.")
    return wrapper


def finance_required(view_func):
    """Decorator requiring finance role or higher."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_finance_user:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("Finance access required.")
    return wrapper


def client_or_staff_required(view_func):
    """Decorator allowing clients and staff."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff_user or request.user.is_client_user:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("Client or staff access required.")
    return wrapper


def prospect_upgrade_required(view_func):
    """Redirect prospects to upgrade page."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_prospect_user:
            messages.info(request, "Please complete your profile to access this feature.")
            return redirect('accounts:profile_edit')
        return view_func(request, *args, **kwargs)
    return wrapper
