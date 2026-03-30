"""
Custom decorators for the MTG Portal.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def staff_required(view_func):
    """
    Decorator that requires the user to be authenticated and be a staff member.
    Redirects to login if not authenticated, or shows an error if not staff.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_staff:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('public:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """
    Decorator that requires the user to be authenticated and be a superuser.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_superuser:
            messages.error(request, 'Administrator access required.')
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return wrapper


def client_required(view_func):
    """
    Decorator that requires the user to be authenticated and be associated with a client.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        # Check if user has an associated contact in CRM
        if not hasattr(request.user, 'contact') or not request.user.contact:
            messages.error(request, 'Client access required.')
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return wrapper


def role_required(*roles):
    """
    Decorator that requires the user to have one of the specified roles.
    Usage: @role_required('admin', 'manager')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            user_role = getattr(request.user, 'role', None)
            if user_role not in roles:
                messages.error(request, 'You do not have the required role to access this page.')
                return redirect('dashboard:index')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
