"""
Admin configuration for jobs app.
"""

from django.contrib import admin
from .models import Job, JobOperation, JobVariant


class JobOperationInline(admin.TabularInline):
    """Inline admin for JobOperation."""
    model = JobOperation
    extra = 0
    readonly_fields = ['created_at']
    fields = [
        'sequence_order', 'operation', 'operation_name', 'quantity_before',
        'quantity_after', 'total_cost', 'total_time_minutes'
    ]


class JobVariantInline(admin.TabularInline):
    """Inline admin for JobVariant."""
    model = JobVariant
    extra = 0
    readonly_fields = ['created_at']
    fields = [
        'quantity', 'total_cost', 'total_time_minutes'
    ]


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    """Admin for Job model."""
    list_display = [
        'job_number', 'client', 'order_type', 'quantity',
        'status', 'is_template', 'total_cost', 'created_at'
    ]
    list_filter = [
        'status', 'order_type', 'is_template', 'created_at',
        'paper_type'
    ]
    search_fields = [
        'job_number', 'client__company_name', 'order_name', 'template_name'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    inlines = [JobOperationInline, JobVariantInline]

    fieldsets = (
        ('Job Information', {
            'fields': (
                'job_number', 'client', 'order_type', 'order_name',
                'quantity', 'status', 'notes'
            )
        }),
        ('Paper Specifications', {
            'fields': (
                'paper_type', 'end_size', 'printing_size', 'selling_size',
                'parts_of_selling_size'
            )
        }),
        ('Production Settings', {
            'fields': (
                'n_up', 'colors_front', 'colors_back', 'special_colors'
            )
        }),
        ('Book-Specific', {
            'fields': ('number_of_pages', 'n_up_signatures'),
            'classes': ('collapse',)
        }),
        ('Template Settings', {
            'fields': ('is_template', 'template_name'),
            'classes': ('collapse',)
        }),
        ('Quantity Variants', {
            'fields': ('variant_quantities',),
            'classes': ('collapse',)
        }),
        ('Calculated Results', {
            'fields': (
                'total_material_cost', 'total_labor_cost', 'total_outsourcing_cost',
                'total_time_minutes', 'print_run', 'waste_sheets', 'sheets_to_buy',
                'paper_weight_kg'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at', 'calculated_at'),
            'classes': ('collapse',)
        })
    )

    readonly_fields = ['created_at', 'updated_at', 'calculated_at']

    actions = ['mark_as_sent', 'mark_as_approved', 'create_templates']

    def mark_as_sent(self, request, queryset):
        """Mark selected jobs as sent to client."""
        queryset.update(status='sent')
    mark_as_sent.short_description = "Mark as sent to client"

    def mark_as_approved(self, request, queryset):
        """Mark selected jobs as approved."""
        queryset.update(status='approved')
    mark_as_approved.short_description = "Mark as approved"

    def create_templates(self, request, queryset):
        """Convert selected jobs to templates."""
        for job in queryset:
            if not job.is_template:
                job.is_template = True
                job.template_name = f"{job.order_type.title()} Template"
                job.save()
    create_templates.short_description = "Convert to templates"


@admin.register(JobOperation)
class JobOperationAdmin(admin.ModelAdmin):
    """Admin for JobOperation model."""
    list_display = [
        'job', 'sequence_order', 'operation_name', 'quantity_before',
        'quantity_after', 'total_cost', 'total_time_minutes'
    ]
    list_filter = ['operation']
    search_fields = ['job__job_number', 'job__client__company_name', 'operation_name']
    ordering = ['job', 'sequence_order']

    readonly_fields = ['created_at']


@admin.register(JobVariant)
class JobVariantAdmin(admin.ModelAdmin):
    """Admin for JobVariant model."""
    list_display = [
        'job', 'quantity', 'total_cost', 'cost_per_piece', 'total_time_minutes'
    ]
    list_filter = ['quantity']
    search_fields = ['job__job_number', 'job__client__company_name']
    ordering = ['job', 'quantity']

    readonly_fields = ['created_at']