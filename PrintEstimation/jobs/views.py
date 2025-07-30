"""
Views for jobs app - job and estimation management.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, ListView, DetailView, UpdateView, DeleteView, TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Job, JobOperation, JobVariant
from .forms import JobForm, JobOperationForm
from .services import PrintingCalculator, JobOperationManager
from PrintEstimation.accounts.models import Client
from PrintEstimation.operations.models import Operation


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view."""
    template_name = 'jobs/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Staff can see all jobs, regular users only their own
        if self.request.user.is_staff_user():
            # Staff users see all jobs
            base_filter = {'is_template': False}
            templates_filter = {'is_template': True}
        else:
            # Regular users see only their jobs
            base_filter = {'created_by': self.request.user, 'is_template': False}
            templates_filter = {'created_by': self.request.user, 'is_template': True}

        # Get workflow-based job categories
        urgent_jobs = Job.objects.filter(**base_filter, status='urgent').order_by('-created_at')
        approved_jobs = Job.objects.filter(**base_filter, status='approved').order_by('-created_at')
        waiting_manager_jobs = Job.objects.filter(**base_filter, status='waiting_manager').order_by('-created_at')
        waiting_client_jobs = Job.objects.filter(**base_filter, status='waiting_client').order_by('-created_at')

        # Get recent jobs (all active statuses)
        context['recent_jobs'] = Job.objects.filter(
            **base_filter
        ).exclude(status__in=['finished', 'rejected']).order_by('-created_at')[:10]

        # Get workflow statistics and job lists
        context.update({
            'urgent_jobs': urgent_jobs,
            'urgent_count': urgent_jobs.count(),
            'approved_jobs': approved_jobs,
            'approved_count': approved_jobs.count(),
            'waiting_manager_jobs': waiting_manager_jobs,
            'waiting_manager_count': waiting_manager_jobs.count(),
            'waiting_client_jobs': waiting_client_jobs,
            'waiting_client_count': waiting_client_jobs.count(),
            'total_templates': Job.objects.filter(**templates_filter).count(),
            'total_active_jobs': Job.objects.filter(**base_filter).exclude(status__in=['finished', 'rejected']).count(),
        })

        return context


class JobListView(LoginRequiredMixin, ListView):
    """List all jobs (non-templates)."""
    model = Job
    template_name = 'jobs/job_list.html'
    context_object_name = 'jobs'
    paginate_by = 20

    def get_queryset(self):
        # Staff can see all jobs, regular users only see their own
        if self.request.user.is_staff_user():
            queryset = Job.objects.filter(is_template=False)
        else:
            queryset = Job.objects.filter(
                created_by=self.request.user,
                is_template=False
            )

        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                order_name__icontains=search
            )

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Job.STATUS_CHOICES
        context['current_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('search', '')
        return context


class JobDetailView(LoginRequiredMixin, DetailView):
    """Job detail view with calculation breakdown."""
    model = Job
    template_name = 'jobs/job_unified.html'
    context_object_name = 'job'

    def get_queryset(self):
        # Staff can view all jobs, regular users only their own
        if self.request.user.is_staff_user():
            return Job.objects.all()
        else:
            return Job.objects.filter(created_by=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get job operations in order
        context['job_operations'] = self.object.job_operations.all().order_by('sequence_order')

        # Get quantity variants
        context['variants'] = self.object.variants.all().order_by('quantity')

        # Set view mode for template
        context['view_mode'] = 'detail'

        return context

    def post(self, request, *args, **kwargs):
        """Handle calculation request from detail view."""
        job = self.get_object()

        try:
            calculator = PrintingCalculator(job)
            result = calculator.calculate_job()

            if result['success']:
                messages.success(request, 'Job calculated successfully!')
                return JsonResponse({
                    'success': True,
                    'total_cost': float(result['total_cost']),
                    'total_time': result['total_time_formatted'],
                    'operations_count': len(result['operations'])
                })
            else:
                messages.error(request, result['error'])
                return JsonResponse({
                    'success': False,
                    'error': result['error']
                })

        except Exception as e:
            error_msg = f'Calculation error: {str(e)}'
            messages.error(request, error_msg)
            return JsonResponse({
                'success': False,
                'error': error_msg
            })


class JobCreateView(LoginRequiredMixin, CreateView):
    """Create new job."""
    model = Job
    form_class = JobForm
    template_name = 'jobs/job_form.html'

    def get_initial(self):
        """Pre-fill form with template data if template parameter is provided."""
        initial = super().get_initial()
        
        template_id = self.request.GET.get('template')
        if template_id:
            try:
                template = Job.objects.get(
                    id=template_id, 
                    is_template=True, 
                    created_by=self.request.user
                )
                
                # Copy all relevant fields from template
                initial.update({
                    # 'client': template.client,
                    'order_type': template.order_type,
                    # 'order_name': template.order_name,
                    'quantity': template.quantity,
                    'paper_type': template.paper_type,
                    'end_size': template.end_size,
                    'custom_end_width': template.custom_end_width,
                    'custom_end_height': template.custom_end_height,
                    'printing_size': template.printing_size,
                    'selling_size': template.selling_size,
                    'parts_of_selling_size': template.parts_of_selling_size,
                    'n_up': template.n_up,
                    'colors_front': template.colors_front,
                    'colors_back': template.colors_back,
                    'special_colors': template.special_colors,
                    'number_of_pages': template.number_of_pages,
                    'n_up_signatures': template.n_up_signatures,
                    'notes': template.notes,
                    # Don't copy template fields for new job
                    'is_template': False,
                    'template_name': '',
                })
                
            except Job.DoesNotExist:
                messages.warning(self.request, 'Template not found or access denied.')
        
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['operations'] = Operation.objects.filter(is_active=True)
        
        # Add template info to context if using template
        template_id = self.request.GET.get('template')
        if template_id:
            try:
                template = Job.objects.get(
                    id=template_id, 
                    is_template=True, 
                    created_by=self.request.user
                )
                context['using_template'] = template
            except Job.DoesNotExist:
                pass
        
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        # Clear template-specific fields when creating a new job
        if not form.instance.is_template:
            form.instance.template_name = ''
        
        response = super().form_valid(form)
        
        # Handle operations for new job creation
        selected_operations = self.request.POST.get('selected_operations')
        if selected_operations:
            try:
                import json
                operations_data = json.loads(selected_operations)
                for op_data in operations_data:
                    operation = Operation.objects.get(id=op_data['operation_id'])
                    JobOperation.objects.create(
                        job=self.object,
                        operation=operation,
                        sequence_order=op_data['sequence_order'],
                        operation_name=operation.name,
                        makeready_price=operation.makeready_price,
                        price_per_sheet=operation.price_per_sheet,
                        plate_price=operation.plate_price,
                        makeready_time_minutes=operation.makeready_time_minutes,
                        cleaning_time_minutes=operation.cleaning_time_minutes,
                        sheets_per_minute=operation.sheets_per_minute,
                        operation_parameters=op_data.get('parameters'),  # Save parameters
                        quantity_before=0,
                        quantity_after=0,
                        waste_sheets=0,
                        processing_quantity=0,
                        total_cost=0,
                        total_time_minutes=0,
                        colors_used=0,
                    )
                messages.success(
                    self.request, 
                    f'Job "{form.instance.order_name}" created with {len(operations_data)} operations!'
                )
                return response
            except (json.JSONDecodeError, Operation.DoesNotExist, KeyError) as e:
                messages.warning(self.request, f'Job created but operations could not be added: {str(e)}')
                return response
        
        # Copy operations from template if creating from template
        template_id = self.request.GET.get('template')
        if template_id:
            try:
                template = Job.objects.get(
                    id=template_id, 
                    is_template=True, 
                    created_by=self.request.user
                )
                
                # Copy operations from template
                for template_operation in template.job_operations.all().order_by('sequence_order'):
                    JobOperation.objects.create(
                        job=self.object,
                        operation=template_operation.operation,
                        sequence_order=template_operation.sequence_order,
                        operation_name=template_operation.operation_name,
                        makeready_price=template_operation.makeready_price,
                        price_per_sheet=template_operation.price_per_sheet,
                        plate_price=template_operation.plate_price,
                        makeready_time_minutes=template_operation.makeready_time_minutes,
                        cleaning_time_minutes=template_operation.cleaning_time_minutes,
                        sheets_per_minute=template_operation.sheets_per_minute,
                        quantity_before=0,  # Will be calculated
                        quantity_after=0,   # Will be calculated
                        processing_quantity=0,  # Will be calculated
                        total_cost=0,       # Will be calculated
                        total_time_minutes=0,  # Will be calculated
                    )
                
                messages.success(
                    self.request, 
                    f'Job "{form.instance.order_name}" created from template "{template.template_name or template.order_name}" with {template.job_operations.count()} operations!'
                )
            except Job.DoesNotExist:
                messages.success(self.request, f'Job "{form.instance.order_name}" created successfully!')
        else:
            messages.success(self.request, f'Job "{form.instance.order_name}" created successfully!')
        
        return response


class JobUpdateView(LoginRequiredMixin, UpdateView):
    """Update existing job."""
    model = Job
    form_class = JobForm
    template_name = 'jobs/job_form.html'
    

    def get_queryset(self):
        # Staff can edit all jobs, regular users only their own
        if self.request.user.is_staff_user():
            return Job.objects.all()
        else:
            return Job.objects.filter(created_by=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['operations'] = Operation.objects.filter(is_active=True)
        context['job_operations'] = self.object.job_operations.all().order_by('sequence_order')
        return context

    def form_valid(self, form):
        messages.success(self.request, f'Job "{form.instance.order_name}" updated successfully!')
        return super().form_valid(form)


class JobDeleteView(LoginRequiredMixin, DeleteView):
    """Delete job."""
    model = Job
    template_name = 'jobs/job_confirm_delete.html'
    success_url = reverse_lazy('jobs:list')

    def get_queryset(self):
        # Only superusers can delete jobs, staff cannot
        if self.request.user.is_superuser:
            return Job.objects.all()
        else:
            return Job.objects.filter(created_by=self.request.user)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.success(request, f'Job "{self.object.order_name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)


class JobCalculateView(LoginRequiredMixin, DetailView):
    """Calculate job costs and generate breakdown."""
    model = Job
    template_name = 'jobs/job_unified.html'
    context_object_name = 'job'

    def get_queryset(self):
        # Staff can calculate all jobs, regular users only their own
        if self.request.user.is_staff_user():
            return Job.objects.all()
        else:
            return Job.objects.filter(created_by=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['job_operations'] = self.object.job_operations.all().order_by('sequence_order')
        
        # Set view mode for template
        context['view_mode'] = 'calculate'
        
        return context

    def post(self, request, *args, **kwargs):
        """Handle calculation request."""
        job = self.get_object()

        try:
            calculator = PrintingCalculator(job)
            result = calculator.calculate_job()

            if result['success']:
                messages.success(request, 'Job calculated successfully!')
                return JsonResponse({
                    'success': True,
                    'total_cost': float(result['total_cost']),
                    'total_time': result['total_time_formatted'],
                    'operations_count': len(result['operations'])
                })
            else:
                messages.error(request, result['error'])
                return JsonResponse({
                    'success': False,
                    'error': result['error']
                })

        except Exception as e:
            error_msg = f'Calculation error: {str(e)}'
            messages.error(request, error_msg)
            return JsonResponse({
                'success': False,
                'error': error_msg
            })


@require_POST
def add_operation_to_job(request, job_id):
    """Add an operation to a job via AJAX."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'})

    try:
        job = get_object_or_404(Job, id=job_id, created_by=request.user)
        operation_id = request.POST.get('operation_id')
        operation = get_object_or_404(Operation, id=operation_id, is_active=True)

        # Add operation to job
        job_operation = JobOperationManager.add_operation(job, operation)

        return JsonResponse({
            'success': True,
            'operation': {
                'id': job_operation.id,
                'name': job_operation.operation_name,
                'sequence_order': job_operation.sequence_order,
                'category': job_operation.operation.category.name
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_POST
def change_job_status(request, pk):
    """Change job status via AJAX."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'})

    try:
        # Staff can change status of all jobs, regular users only their own
        if request.user.is_staff_user():
            job = get_object_or_404(Job, id=pk)
        else:
            job = get_object_or_404(Job, id=pk, created_by=request.user)

        data = json.loads(request.body)
        new_status = data.get('status')

        # Validate status
        valid_statuses = [choice[0] for choice in Job.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': 'Invalid status'})

        # Update job status
        old_status = job.get_status_display()
        job.status = new_status
        job.save()

        return JsonResponse({
            'success': True,
            'message': f'Status changed from "{old_status}" to "{job.get_status_display()}"',
            'new_status': new_status,
            'new_status_display': job.get_status_display()
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
def remove_operation_from_job(request, job_id, operation_id):
    """Remove an operation from a job via AJAX."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'})

    try:
        job = get_object_or_404(Job, id=job_id, created_by=request.user)
        job_operation = get_object_or_404(JobOperation, id=operation_id, job=job)

        JobOperationManager.remove_operation(job_operation)

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


class ReorderOperationsView(LoginRequiredMixin, DetailView):
    """Reorder operations in a job via AJAX."""
    model = Job

    def get_queryset(self):
        return Job.objects.filter(created_by=self.request.user)

    def post(self, request, *args, **kwargs):
        job = self.get_object()

        try:
            # Debug logging
            print(f"Reorder request for job {job.id}")
            print(f"Request body: {request.body}")
            
            data = json.loads(request.body)
            operation_ids = data.get('operation_ids', [])
            
            print(f"Operation IDs to reorder: {operation_ids}")
            
            if not operation_ids:
                return JsonResponse({
                    'success': False,
                    'error': 'No operation IDs provided'
                })

            # Validate that all operation IDs belong to this job
            existing_operations = set(
                job.job_operations.values_list('id', flat=True)
            )
            provided_operations = set(int(op_id) for op_id in operation_ids if str(op_id).isdigit())
            
            print(f"Existing operations: {existing_operations}")
            print(f"Provided operations: {provided_operations}")
            
            if not provided_operations.issubset(existing_operations):
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid operation IDs provided'
                })

            JobOperationManager.reorder_operations(job, operation_ids)
            
            print("Reorder completed successfully")
            return JsonResponse({'success': True})

        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Invalid JSON data: {str(e)}'
            })
        except ValueError as e:
            print(f"Validation error: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Validation error: {str(e)}'
            })
        except Exception as e:
            print(f"Reorder error: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'error': f'Database error: {str(e)}'
            })


class TemplateListView(LoginRequiredMixin, ListView):
    """List all templates."""
    model = Job
    template_name = 'jobs/template_list.html'
    context_object_name = 'templates'
    paginate_by = 20

    def get_queryset(self):
        # Staff can see all templates, regular users only see their own
        if self.request.user.is_staff_user():
            queryset = Job.objects.filter(is_template=True)
        else:
            queryset = Job.objects.filter(
                created_by=self.request.user,
                is_template=True
            )

        # Filter by order type
        order_type = self.request.GET.get('type')
        if order_type:
            queryset = queryset.filter(order_type=order_type)

        return queryset.order_by('order_type', 'template_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order_types'] = Job.ORDER_TYPES
        context['current_type'] = self.request.GET.get('type', '')
        return context