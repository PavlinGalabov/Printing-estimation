"""
Admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin for User model.
    """
    # Display configuration
    list_display = ['username', 'email', 'get_full_name', 'company_name', 'user_type', 'is_active', 'date_joined']
    list_filter = ['user_type', 'is_active', 'is_staff', 'is_superuser', 'date_joined']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'company_name']
    ordering = ['-date_joined']

    # Form configuration
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'company_name', 'phone', 'address', 'notes')
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'company_name', 'phone', 'address')
        }),
    )

    # Actions
    actions = ['make_staff', 'make_client']

    def make_staff(self, request, queryset):
        """Action to make selected users staff."""
        queryset.update(user_type='staff')

    make_staff.short_description = "Mark selected users as staff"

    def make_client(self, request, queryset):
        """Action to make selected users clients."""
        queryset.update(user_type='client')

    make_client.short_description = "Mark selected users as clients"