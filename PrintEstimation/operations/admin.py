"""
Admin configuration for operations app.
"""

from django.contrib import admin
from .models import (
    OperationCategory, Operation, PaperType,
    PaperSize, PrintingMachine
)


@admin.register(OperationCategory)
class OperationCategoryAdmin(admin.ModelAdmin):
    """Admin for OperationCategory model."""
    list_display = ['name', 'color', 'sort_order']
    list_editable = ['sort_order']
    search_fields = ['name']
    ordering = ['sort_order', 'name']


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    """Admin for Operation model."""
    list_display = [
        'name', 'category', 'pricing_type', 'makeready_price',
        'price_per_unit', 'is_active'
    ]
    list_filter = ['category', 'pricing_type', 'is_active', 'requires_colors']
    search_fields = ['name', 'description']
    ordering = ['category__sort_order', 'name']
    list_editable = ['makeready_price', 'price_per_unit', 'is_active']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'description', 'pricing_type', 'is_active')
        }),
        ('Pricing', {
            'fields': ('makeready_price', 'price_per_unit', 'outsourcing_rate'),
            'description': 'Configure pricing based on the selected pricing type'
        }),
        ('Time Calculations', {
            'fields': ('makeready_time_minutes', 'time_per_unit_seconds')
        }),
        ('Quantity Effects', {
            'fields': ('divides_quantity_by', 'multiplies_quantity_by'),
            'description': 'How this operation affects the quantity for subsequent operations'
        }),
        ('Advanced', {
            'fields': ('requires_colors', 'custom_cost_formula', 'custom_time_formula'),
            'classes': ('collapse',)
        })
    )

    actions = ['activate_operations', 'deactivate_operations']

    def activate_operations(self, request, queryset):
        """Activate selected operations."""
        queryset.update(is_active=True)

    activate_operations.short_description = "Activate selected operations"

    def deactivate_operations(self, request, queryset):
        """Deactivate selected operations."""
        queryset.update(is_active=False)

    deactivate_operations.short_description = "Deactivate selected operations"


@admin.register(PaperType)
class PaperTypeAdmin(admin.ModelAdmin):
    """Admin for PaperType model."""
    list_display = ['name', 'weight_gsm', 'price_per_kg', 'is_active']
    list_filter = ['is_active', 'weight_gsm']
    search_fields = ['name']
    ordering = ['name']
    list_editable = ['price_per_kg', 'is_active']


@admin.register(PaperSize)
class PaperSizeAdmin(admin.ModelAdmin):
    """Admin for PaperSize model."""
    list_display = ['name', 'width_cm', 'height_cm', 'area_cm2', 'is_standard']
    list_filter = ['is_standard']
    search_fields = ['name']
    ordering = ['name']
    list_editable = ['is_standard']

    def area_cm2(self, obj):
        """Display area in cm²."""
        return f"{obj.area_cm2:.1f} cm²"

    area_cm2.short_description = "Area"


@admin.register(PrintingMachine)
class PrintingMachineAdmin(admin.ModelAdmin):
    """Admin for PrintingMachine model."""
    list_display = [
        'name', 'max_paper_width_cm', 'max_paper_height_cm',
        'max_colors', 'cost_per_hour', 'is_active'
    ]
    list_filter = ['is_active', 'max_colors']
    search_fields = ['name']
    ordering = ['name']
    list_editable = ['cost_per_hour', 'is_active']