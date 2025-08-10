"""
Admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.http import JsonResponse
from .models import User, Client


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin for User model.
    """
    # Display configuration
    list_display = ['username', 'email', 'get_full_name', 'user_type', 'is_active', 'last_login', 'date_joined']
    list_filter = ['user_type', 'is_active', 'is_staff', 'is_superuser', 'date_joined', 'last_login']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'phone']
    ordering = ['-date_joined']
    list_per_page = 25
    date_hierarchy = 'date_joined'

    # Form configuration
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'phone', 'notes')
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'phone')
        }),
    )

    # Actions
    actions = ['make_staff', 'make_client', 'make_superuser_type']

    def has_change_permission(self, request, obj=None):
        """Control who can change user roles."""
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Control who can delete users."""
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        """Override save to add security checks and group management."""
        # Security check: Only superusers can create/modify other superusers
        if obj.user_type == 'superuser' and not request.user.is_superuser:
            messages.error(request, "Only superusers can create or modify superuser accounts.")
            return
        
        # If demoting a superuser, only allow if current user is also superuser
        if change and obj.user_type != 'superuser':
            original = User.objects.get(pk=obj.pk)
            if original.user_type == 'superuser' and not request.user.is_superuser:
                messages.error(request, "Only superusers can demote other superusers.")
                return
        
        # Save the user
        super().save_model(request, obj, form, change)
        
        # Manage groups and permissions based on user_type
        self._update_user_groups(obj)
        
        # Log the change
        if change:
            messages.success(request, f'User "{obj.username}" role updated to {obj.get_user_type_display()}.')

    def _update_user_groups(self, user):
        """Update user groups based on user_type."""
        # Clear all groups first
        user.groups.clear()
        
        try:
            if user.user_type == 'staff':
                staff_group = Group.objects.get(name='Staff')
                user.groups.add(staff_group)
                # Ensure staff flag is set
                if not user.is_staff:
                    user.is_staff = True
                    user.save()
            elif user.user_type == 'superuser':
                managers_group, _ = Group.objects.get_or_create(name='Managers')
                user.groups.add(managers_group)
                # Ensure superuser and staff flags are set
                if not user.is_superuser or not user.is_staff:
                    user.is_superuser = True
                    user.is_staff = True
                    user.save()
            # Clients don't get any groups
        except Group.DoesNotExist:
            pass  # Groups not set up yet

    def make_staff(self, request, queryset):
        """Action to make selected users staff."""
        if not request.user.is_superuser:
            self.message_user(request, "Only superusers can change user roles.", level=messages.ERROR)
            return
        
        updated = 0
        for user in queryset:
            if user.user_type != 'superuser':  # Don't demote superusers
                user.user_type = 'staff'
                user.save()
                self._update_user_groups(user)
                updated += 1
        
        self.message_user(request, f'{updated} users changed to staff.')
    make_staff.short_description = "Mark selected users as staff"

    def make_client(self, request, queryset):
        """Action to make selected users clients."""
        if not request.user.is_superuser:
            self.message_user(request, "Only superusers can change user roles.", level=messages.ERROR)
            return
        
        updated = 0
        for user in queryset:
            if user.user_type != 'superuser':  # Don't demote superusers
                user.user_type = 'client'
                user.is_staff = False  # Remove staff privileges
                user.save()
                self._update_user_groups(user)
                updated += 1
        
        self.message_user(request, f'{updated} users changed to client.')
    make_client.short_description = "Mark selected users as clients"

    def make_superuser_type(self, request, queryset):
        """Action to make selected users superuser type (only for superusers)."""
        if not request.user.is_superuser:
            self.message_user(request, "Only superusers can create other superusers.", level=messages.ERROR)
            return
        
        updated = 0
        for user in queryset:
            user.user_type = 'superuser'
            user.save()
            self._update_user_groups(user)
            updated += 1
        
        self.message_user(request, f'{updated} users promoted to superuser.')
    make_superuser_type.short_description = "Promote to superuser (Superuser only)"


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """
    Admin for Client model.
    """
    list_display = [
        'company_name', 'contact_person', 'email', 'phone',
        'payment_terms', 'is_active', 'is_vip', 'created_at'
    ]
    list_filter = [
        'is_active', 'is_vip', 'payment_terms', 'country', 'created_at'
    ]
    search_fields = [
        'company_name', 'contact_person', 'email', 'phone', 'tax_number'
    ]
    ordering = ['company_name']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'company_name', 'contact_person', 'email', 'phone', 'mobile', 'website'
            )
        }),
        ('Address', {
            'fields': (
                'address_line_1', 'address_line_2', 'city', 'state_province',
                'postal_code', 'country'
            )
        }),
        ('Business Details', {
            'fields': (
                'tax_number', 'payment_terms', 'credit_limit', 'discount_percentage'
            )
        }),
        ('Notes and Requirements', {
            'fields': ('notes', 'special_requirements')
        }),
        ('Status and Settings', {
            'fields': ('is_active', 'is_vip', 'user')
        })
    )

    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 20
    list_editable = ['is_active', 'is_vip', 'payment_terms']

    actions = ['mark_as_vip', 'mark_as_regular', 'activate_clients', 'deactivate_clients', 'export_selected']

    def mark_as_vip(self, request, queryset):
        """Mark selected clients as VIP."""
        queryset.update(is_vip=True)
    mark_as_vip.short_description = "Mark as VIP clients"

    def mark_as_regular(self, request, queryset):
        """Remove VIP status from selected clients."""
        queryset.update(is_vip=False)
    mark_as_regular.short_description = "Remove VIP status"

    def activate_clients(self, request, queryset):
        """Activate selected clients."""
        queryset.update(is_active=True)
    activate_clients.short_description = "Activate selected clients"

    def deactivate_clients(self, request, queryset):
        """Deactivate selected clients."""
        queryset.update(is_active=False)
    deactivate_clients.short_description = "Deactivate selected clients"

    def export_selected(self, request, queryset):
        """Export selected clients (placeholder)."""
        self.message_user(request, f"Would export {queryset.count()} clients")
    export_selected.short_description = "Export selected clients"