"""
Permission mixins for class-based views.
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin requiring staff role or higher."""
    
    def test_func(self):
        return self.request.user.is_staff_user
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("Staff access required.")
        return super().handle_no_permission()


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin requiring admin role."""
    
    def test_func(self):
        return self.request.user.is_admin_user
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("Administrator access required.")
        return super().handle_no_permission()


class FinanceRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin requiring finance role or higher."""
    
    def test_func(self):
        return self.request.user.is_finance_user
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("Finance access required.")
        return super().handle_no_permission()


class ClientOrStaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin allowing clients and staff."""
    
    def test_func(self):
        return self.request.user.is_staff_user or self.request.user.is_client_user
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("Client or staff access required.")
        return super().handle_no_permission()


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Generic mixin for role checking.
    Set required_roles as a list of role names.
    """
    required_roles = []
    
    def test_func(self):
        return self.request.user.has_any_role(*self.required_roles)
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().handle_no_permission()


class OwnerOrStaffMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin that allows object owner or staff to access.
    Requires the view to have get_object() method.
    Set owner_field to specify the field name containing the owner.
    """
    owner_field = 'user'
    
    def test_func(self):
        if self.request.user.is_staff_user:
            return True
        obj = self.get_object()
        owner = getattr(obj, self.owner_field, None)
        return owner == self.request.user
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("You don't have permission to access this resource.")
        return super().handle_no_permission()


class OrganizationMemberMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin that checks if user belongs to the same organization.
    For clients viewing their organization's data.
    """
    organization_field = 'organization'
    
    def test_func(self):
        if self.request.user.is_staff_user:
            return True
        if not self.request.user.organization:
            return False
        obj = self.get_object()
        org = getattr(obj, self.organization_field, None)
        return org == self.request.user.organization
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("You don't have permission to access this resource.")
        return super().handle_no_permission()
