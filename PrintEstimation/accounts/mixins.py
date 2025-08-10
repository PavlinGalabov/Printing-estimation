"""
Security mixins for enhanced permission control.
"""

from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import redirect


class SuperuserRequiredMixin(UserPassesTestMixin):
    """
    Mixin to require superuser access.
    More secure than just checking is_superuser flag.
    """

    def test_func(self):
        return (
            self.request.user.is_authenticated and 
            self.request.user.is_superuser and 
            self.request.user.user_type == 'superuser'
        )
    
    def handle_no_permission(self):
        messages.error(self.request, "Access denied. Superuser privileges required.")
        return redirect('core:home')


class StaffRequiredMixin(UserPassesTestMixin):
    """
    Mixin to require staff-level access (staff or superuser).
    """

    def test_func(self):
        return (
            self.request.user.is_authenticated and 
            self.request.user.is_staff_user()
        )
    
    def handle_no_permission(self):
        messages.error(self.request, "Access denied. Staff privileges required.")
        return redirect('core:home')


class OwnerRequiredMixin:
    """
    Mixin to ensure users can only access their own content.
    Requires the model to have a 'created_by' field.
    """
    
    def get_queryset(self):
        """Filter queryset to show only user's own objects."""
        queryset = super().get_queryset()
        
        if self.request.user.is_staff_user():
            # Staff can see all objects
            return queryset
        else:
            # Regular users see only their own
            return queryset.filter(created_by=self.request.user)
    
    def get_object(self, queryset=None):
        """Ensure user can only access their own objects."""
        obj = super().get_object(queryset)
        
        # Staff can access any object
        if self.request.user.is_staff_user():
            return obj
        
        # Regular users can only access their own objects
        if hasattr(obj, 'created_by') and obj.created_by != self.request.user:
            raise PermissionDenied("You can only access your own content.")
        
        return obj


class SecureFormMixin:
    """
    Mixin for forms that need additional security validation.
    """
    
    def form_valid(self, form):
        """Add security checks before saving."""
        # Ensure regular users can only create content for themselves
        if hasattr(form.instance, 'created_by') and not form.instance.created_by:
            form.instance.created_by = self.request.user
        
        return super().form_valid(form)