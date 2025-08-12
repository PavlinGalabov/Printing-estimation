"""
Views for jobs app - job and estimation management.
"""

from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    CreateView, ListView, DetailView, UpdateView, DeleteView, TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin
from PrintEstimation.accounts.mixins import OwnerRequiredMixin, SecureFormMixin, StaffRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Job, JobOperation, JobVariant, JobPDFExport
from .forms import (
    JobForm, JobOperationForm, JobStatusChangeForm, JobCalculationForm,
    AddOperationForm, AddOperationAfterForm, RemoveOperationForm, ReorderOperationsForm,
    JobVariantForm, MultiQuantityForm, CalculateVariantsForm
)
from .services import PrintingCalculator, JobOperationManager
from PrintEstimation.accounts.models import Client
from PrintEstimation.operations.models import Operation



class JobListView(LoginRequiredMixin, OwnerRequiredMixin, ListView):
    """List all jobs (non-templates)."""
    model = Job
    template_name = 'jobs/job_list.html'
    context_object_name = 'jobs'
    paginate_by = 20

    def get_queryset(self):
        # Use the parent mixin for ownership filtering, then add our filter
        queryset = super().get_queryset().filter(is_template=False)

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


class JobDetailView(LoginRequiredMixin, OwnerRequiredMixin, DetailView):
    """Job detail view with calculation breakdown."""
    model = Job
    template_name = 'jobs/job_detail.html'
    context_object_name = 'job'

    # Remove get_queryset - handled by OwnerRequiredMixin

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get job operations in order
        context['job_operations'] = self.object.job_operations.all().order_by('sequence_order')

        # Get quantity variants
        context['variants'] = self.object.variants.all().order_by('quantity')

        # Set view mode for template
        context['view_mode'] = 'detail'

        # Add forms for Python-based interactions
        context['status_form'] = JobStatusChangeForm(instance=self.object)
        context['calculation_form'] = JobCalculationForm()
        context['add_operation_form'] = AddOperationForm()
        context['reorder_form'] = ReorderOperationsForm(job=self.object)
        
        # Add available operations for adding
        context['available_operations'] = Operation.objects.filter(is_active=True).order_by('category__sort_order', 'name')
        
        # Add variant forms and data
        context['multi_quantity_form'] = MultiQuantityForm()
        context['calculate_variants_form'] = CalculateVariantsForm(job=self.object)
        
        # Add existing variants
        context['variants'] = self.object.variants.all().order_by('quantity')

        return context

    def post(self, request, *args, **kwargs):
        """Handle form submissions from detail view (status change, calculation, operations)."""
        job = self.get_object()
        
        # Handle status change
        if 'change_status' in request.POST:
            status_form = JobStatusChangeForm(request.POST, instance=job)
            if status_form.is_valid():
                old_status = job.get_status_display()
                status_form.save()
                new_status = job.get_status_display()
                messages.success(request, f'Status changed from "{old_status}" to "{new_status}"')
            else:
                messages.error(request, 'Error changing status. Please try again.')
            return redirect('jobs:detail', pk=job.pk)
        
        # Handle calculation  
        elif 'calculate' in request.POST:
            try:
                calculator = PrintingCalculator(job)
                result = calculator.calculate_job()
                
                if result['success']:
                    messages.success(request, 'Job calculated successfully!')
                else:
                    messages.error(request, f'Calculation error: {result["error"]}')
            except Exception as e:
                messages.error(request, f'Calculation error: {str(e)}')
            return redirect('jobs:detail', pk=job.pk)
        
        # Handle add operation
        elif 'add_operation' in request.POST:
            add_form = AddOperationForm(request.POST)
            if add_form.is_valid():
                operation = add_form.cleaned_data['operation']
                try:
                    job_operation = JobOperationManager.add_operation(job, operation)
                    messages.success(request, f'Added operation: {operation.name}')
                except Exception as e:
                    messages.error(request, f'Error adding operation: {str(e)}')
            else:
                messages.error(request, 'Please select a valid operation.')
            return redirect('jobs:detail', pk=job.pk)
        
        # Handle add operation after specific position (with anchor)
        elif 'add_operation_after' in request.POST:
            add_after_form = AddOperationAfterForm(request.POST)
            if add_after_form.is_valid():
                operation = add_after_form.cleaned_data['operation']
                after_operation_id = add_after_form.cleaned_data['after_operation_id']
                operation_parameters = add_after_form.cleaned_data.get('operation_parameters', {})
                try:
                    from django.db import transaction, models
                    
                    with transaction.atomic():
                        # Get the operation after which to insert
                        after_operation = JobOperation.objects.get(id=after_operation_id, job=job)
                        target_sequence = after_operation.sequence_order + 1
                        
                        # Shift all operations after this position up by 1 (starting from the highest sequence)
                        operations_to_update = JobOperation.objects.filter(
                            job=job, 
                            sequence_order__gte=target_sequence
                        ).order_by('-sequence_order')
                        
                        for op in operations_to_update:
                            op.sequence_order += 1
                            op.save()
                        
                        # Add the new operation at the target position
                        job_operation = JobOperation.objects.create(
                            job=job,
                            operation=operation,
                            sequence_order=target_sequence,
                            operation_name=operation.name,
                            makeready_price=operation.makeready_price,
                            price_per_sheet=operation.price_per_sheet,
                            plate_price=operation.plate_price,
                            makeready_time_minutes=operation.makeready_time_minutes,
                            cleaning_time_minutes=operation.cleaning_time_minutes,
                            sheets_per_minute=operation.sheets_per_minute,
                            operation_parameters=operation_parameters,
                            quantity_before=0,
                            quantity_after=0,
                            waste_sheets=0,
                            processing_quantity=0,
                            total_cost=0,
                            total_time_minutes=0,
                            colors_used=0,
                        )
                    
                    messages.success(request, f'Added "{operation.name}" after "{after_operation.operation_name}"')
                    # Redirect to the operation we added after (to stay in context)
                    return redirect(f"{reverse('jobs:detail', kwargs={'pk': job.pk})}#operation-{after_operation_id}")
                except JobOperation.DoesNotExist:
                    messages.error(request, 'Target operation not found.')
                except Exception as e:
                    messages.error(request, f'Error adding operation: {str(e)}')
            else:
                messages.error(request, 'Please select a valid operation.')
            return redirect('jobs:detail', pk=job.pk)
        
        # Handle remove operation (with anchor)
        elif 'remove_operation' in request.POST:
            remove_form = RemoveOperationForm(request.POST)
            if remove_form.is_valid() and remove_form.cleaned_data['confirm']:
                operation_id = remove_form.cleaned_data['operation_id']
                try:
                    job_operation = JobOperation.objects.get(id=operation_id, job=job)
                    operation_name = job_operation.operation_name
                    # Get the next operation to scroll to (or previous if last)
                    next_operation = job.job_operations.filter(sequence_order__gt=job_operation.sequence_order).first()
                    prev_operation = job.job_operations.filter(sequence_order__lt=job_operation.sequence_order).last()
                    anchor_target = next_operation or prev_operation
                    
                    JobOperationManager.remove_operation(job_operation)
                    messages.success(request, f'Removed operation: {operation_name}')
                    
                    # Redirect to nearby operation if one exists
                    if anchor_target:
                        return redirect(f"{reverse('jobs:detail', kwargs={'pk': job.pk})}#operation-{anchor_target.id}")
                except JobOperation.DoesNotExist:
                    messages.error(request, 'Operation not found.')
                except Exception as e:
                    messages.error(request, f'Error removing operation: {str(e)}')
            else:
                messages.error(request, 'Please confirm operation removal.')
            return redirect('jobs:detail', pk=job.pk)
        
        # Handle add quantities (multiple variants)
        elif 'add_quantities' in request.POST:
            qty_form = MultiQuantityForm(request.POST)
            if qty_form.is_valid():
                quantities = qty_form.cleaned_data['quantities']
                try:
                    # Remove existing variants for these quantities to avoid duplicates
                    job.variants.filter(quantity__in=quantities).delete()
                    
                    # Create new variants (without calculation initially)
                    created = 0
                    for qty in quantities:
                        variant, created_new = JobVariant.objects.get_or_create(
                            job=job,
                            quantity=qty,
                            defaults={
                                'total_cost': 0,
                                'total_time_minutes': 0,
                                'print_run': 0,
                                'waste_sheets': 0,
                                'sheets_to_buy': 0,
                                'paper_weight_kg': 0,
                                'paper_cost': 0,
                                'operations_cost': 0,
                            }
                        )
                        if created_new:
                            created += 1
                    
                    messages.success(request, f'Added {created} quantity variants. Click "Calculate All Variants" to get costs.')
                except Exception as e:
                    messages.error(request, f'Error adding variants: {str(e)}')
            else:
                messages.error(request, 'Please enter valid quantities.')
            return redirect('jobs:detail', pk=job.pk)
        
        # Handle calculate all variants
        elif 'calculate_variants' in request.POST:
            try:
                calculator = PrintingCalculator(job)
                variant_quantities = list(job.variants.values_list('quantity', flat=True))
                
                if not variant_quantities:
                    messages.warning(request, 'No quantity variants found. Add some quantities first.')
                else:
                    result = calculator.calculate_all_variants(variant_quantities)
                    
                    if result['success']:
                        count = len(result['created_variants'])
                        messages.success(request, f'Successfully calculated {count} quantity variants!')
                        
                        if result['failed_calculations']:
                            failed_qty = [str(f['quantity']) for f in result['failed_calculations']]
                            messages.warning(request, f'Failed to calculate: {", ".join(failed_qty)}')
                    else:
                        messages.error(request, f'Calculation error: {result["error"]}')
            except Exception as e:
                messages.error(request, f'Error calculating variants: {str(e)}')
            return redirect('jobs:detail', pk=job.pk)
        
        # Handle delete variant
        elif 'delete_variant' in request.POST:
            variant_id = request.POST.get('variant_id')
            if variant_id:
                try:
                    variant = JobVariant.objects.get(id=variant_id, job=job)
                    quantity = variant.quantity
                    variant.delete()
                    messages.success(request, f'Removed variant for {quantity} pieces.')
                except JobVariant.DoesNotExist:
                    messages.error(request, 'Variant not found.')
                except Exception as e:
                    messages.error(request, f'Error removing variant: {str(e)}')
            return redirect('jobs:detail', pk=job.pk)
        
        # Default redirect (should not reach here)
        return redirect('jobs:detail', pk=job.pk)


class JobCreateView(LoginRequiredMixin, SecureFormMixin, CreateView):
    """Create new job."""
    model = Job
    form_class = JobForm
    template_name = 'jobs/job_form.html'

    def get_initial(self):
        """Pre-fill form with template data if template parameter is provided."""
        initial = super().get_initial()
        
        # Handle client parameter
        client_id = self.request.GET.get('client')
        if client_id:
            try:
                client = Client.objects.get(id=client_id)
                initial['client'] = client
            except Client.DoesNotExist:
                messages.warning(self.request, 'Client not found.')
        
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


class JobUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
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

    def post(self, request, *args, **kwargs):
        """Handle both form updates and calculation requests."""
        # Handle calculation request
        if 'calculate' in request.POST:
            job = self.get_object()
            try:
                calculator = PrintingCalculator(job)
                result = calculator.calculate_job()
                
                if result['success']:
                    messages.success(request, 'Job calculated successfully!')
                else:
                    messages.error(request, f'Calculation error: {result["error"]}')
            except Exception as e:
                messages.error(request, f'Calculation error: {str(e)}')
            return redirect('jobs:detail', pk=job.pk)
        
        # Handle regular form submission
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'Job "{form.instance.order_name}" updated successfully!')
        return super().form_valid(form)


class JobDeleteView(LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
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
        # Use the same queryset logic as JobUpdateView
        if request.user.is_staff_user():
            jobs_queryset = Job.objects.all()
        else:
            jobs_queryset = Job.objects.filter(created_by=request.user)
            
        job = get_object_or_404(jobs_queryset, id=job_id)
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
            
            data = json.loads(request.body)
            operation_ids = data.get('operation_ids', [])
            
            
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
            
            return JsonResponse({'success': True})

        except json.JSONDecodeError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid JSON data: {str(e)}'
            })
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Validation error: {str(e)}'
            })
        except Exception as e:
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


# PDF Export Views

class JobPDFExportListView(LoginRequiredMixin, ListView):
    """List view for PDF exports with filtering and export generation."""
    model = Job
    template_name = 'jobs/pdf_export_list.html'
    context_object_name = 'jobs'
    paginate_by = 20

    def get_queryset(self):
        """Filter jobs that can be exported."""
        queryset = Job.objects.filter(is_template=False)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by client
        client_id = self.request.GET.get('client')
        if client_id:
            queryset = queryset.filter(client_id=client_id)
            
        # Filter calculated jobs only (have cost data)
        calculated_only = self.request.GET.get('calculated_only')
        if calculated_only:
            queryset = queryset.exclude(status='draft')
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Job.STATUS_CHOICES
        context['clients'] = Client.objects.filter(is_active=True)
        context['export_types'] = JobPDFExport.EXPORT_TYPES
        context['current_status'] = self.request.GET.get('status', '')
        context['current_client'] = self.request.GET.get('client', '')
        context['calculated_only'] = self.request.GET.get('calculated_only', '')
        return context


class JobPDFGenerateView(LoginRequiredMixin, DetailView):
    """Generate and download PDF for a specific job."""
    model = Job
    
    def get(self, request, *args, **kwargs):
        job = self.get_object()
        export_type = request.GET.get('type', 'estimate')
        
        # Validate export type
        valid_types = [choice[0] for choice in JobPDFExport.EXPORT_TYPES]
        if export_type not in valid_types:
            raise Http404("Invalid export type")
        
        try:
            from .pdf_service import PDFExportService
            
            # Create the export
            export, html_content = PDFExportService.create_export(job, export_type, request.user)
            
            # Return the HTML file that can be printed as PDF
            response = HttpResponse(html_content, content_type='text/html')
            
            # Add success message for next page visit
            messages.success(request, f'Export "{export.get_export_type_display()}" generated successfully! Use your browser\'s print function to save as PDF.')
            
            return response
            
        except Exception as e:
            messages.error(request, f'Error generating export: {str(e)}')
            return redirect('jobs:pdf_export_list')


class JobPDFHistoryView(LoginRequiredMixin, ListView):
    """View export history for all jobs or a specific job."""
    model = JobPDFExport
    template_name = 'jobs/pdf_export_history.html'
    context_object_name = 'exports'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = JobPDFExport.objects.select_related('job', 'created_by')
        
        # Filter by job if specified
        job_id = self.request.GET.get('job')
        if job_id:
            queryset = queryset.filter(job_id=job_id)
        
        # Filter by export type
        export_type = self.request.GET.get('type')
        if export_type:
            queryset = queryset.filter(export_type=export_type)
        
        # Filter by user
        if not self.request.user.is_superuser:
            queryset = queryset.filter(created_by=self.request.user)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['export_types'] = JobPDFExport.EXPORT_TYPES
        context['current_job'] = self.request.GET.get('job', '')
        context['current_type'] = self.request.GET.get('type', '')
        
        # Add jobs for filtering
        if self.request.user.is_superuser:
            context['jobs'] = Job.objects.filter(is_template=False).order_by('-created_at')[:100]
        else:
            context['jobs'] = Job.objects.filter(is_template=False, created_by=self.request.user).order_by('-created_at')[:100]
        
        return context


class JobPDFDownloadView(LoginRequiredMixin, DetailView):
    """Download a previously generated PDF export."""
    model = JobPDFExport
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Non-superusers can only download their own exports
        if not self.request.user.is_superuser:
            queryset = queryset.filter(created_by=self.request.user)
        return queryset
    
    def get(self, request, *args, **kwargs):
        export = self.get_object()
        
        try:
            # Return HTML content that can be printed as PDF
            content = export.file_path.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            response = HttpResponse(content, content_type='text/html')
            return response
        except FileNotFoundError:
            messages.error(request, 'Export file not found. It may have been deleted.')
            return redirect('jobs:pdf_export_history')


class JobPDFDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a PDF export record and file."""
    model = JobPDFExport
    template_name = 'jobs/pdf_export_confirm_delete.html'
    success_url = reverse_lazy('jobs:pdf_export_history')
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Non-superusers can only delete their own exports
        if not self.request.user.is_superuser:
            queryset = queryset.filter(created_by=self.request.user)
        return queryset
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Delete the actual file
        try:
            if self.object.file_path:
                self.object.file_path.delete(save=False)
        except Exception:
            pass  # File might not exist
        
        messages.success(request, f'PDF export "{self.object.file_name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)