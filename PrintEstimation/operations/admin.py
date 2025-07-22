"""
Admin configuration for operations app with simplified formula approach.
"""

from django.contrib import admin
from .models import OperationCategory, Operation, PaperType, PaperSize


@admin.register(OperationCategory)
class OperationCategoryAdmin(admin.ModelAdmin):
    """Admin for OperationCategory model."""
    list_display = ['name', 'color', 'sort_order']
    list_editable = ['sort_order']
    search_fields = ['name']
    ordering = ['sort_order', 'name']


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    """Admin for Operation model with formula-based pricing."""
    list_display = [
        'name', 'category', 'makeready_price', 'price_per_sheet',
        'uses_colors', 'is_active'
    ]
    list_filter = ['category', 'uses_colors', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['category__sort_order', 'name']
    list_editable = ['makeready_price', 'price_per_sheet', 'is_active']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'description', 'is_active')
        }),
        ('Cost Formula Constants', {
            'fields': ('makeready_price', 'price_per_sheet', 'plate_price'),
            'description': 'Constants used in cost calculation formulas'
        }),
        ('Waste Calculation', {
            'fields': ('base_waste_sheets', 'waste_percentage'),
            'description': 'Parameters for calculating waste sheets'
        }),
        ('Time Formula Constants', {
            'fields': ('makeready_time_minutes', 'cleaning_time_minutes', 'sheets_per_minute'),
            'description': 'Constants used in time calculation formulas'
        }),
        ('Quantity Effects', {
            'fields': ('divides_quantity_by', 'multiplies_quantity_by'),
            'description': 'How this operation affects quantity for subsequent operations'
        }),
        ('Operation Behavior', {
            'fields': ('uses_colors', 'uses_front_colors_only'),
            'description': 'How this operation interacts with color settings'
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