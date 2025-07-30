"""
Admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
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
    actions = ['make_staff', 'make_client']

    def make_staff(self, request, queryset):
        """Action to make selected users staff."""
        queryset.update(user_type='staff')
    make_staff.short_description = "Mark selected users as staff"

    def make_client(self, request, queryset):
        """Action to make selected users clients."""
        queryset.update(user_type='client')
    make_client.short_description = "Mark selected users as clients"


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