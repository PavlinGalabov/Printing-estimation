"""
Views for operations app - operation and material management.
"""

from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, ListView, DetailView, UpdateView, DeleteView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import (
    Operation, OperationCategory, PaperType,
    PaperSize,
)


class SuperuserRequiredMixin(UserPassesTestMixin):
    """Mixin to require superuser access."""

    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.is_superuser_type or self.request.user.is_superuser
        )


# Operation Views

class OperationListView(LoginRequiredMixin, ListView):
    """List all operations."""
    model = Operation
    template_name = 'operations/operation_list.html'
    context_object_name = 'operations'
    paginate_by = 20

    def get_queryset(self):
        queryset = Operation.objects.filter(is_active=True)

        # Filter by category
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)

        return queryset.order_by('category__sort_order', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = OperationCategory.objects.all()
        context['current_category'] = self.request.GET.get('category', '')
        return context


class OperationDetailView(LoginRequiredMixin, DetailView):
    """Operation detail view."""
    model = Operation
    template_name = 'operations/operation_detail.html'
    context_object_name = 'operation'


class OperationCreateView(LoginRequiredMixin, CreateView):
    """Create new operation."""
    model = Operation
    template_name = 'operations/operation_form.html'
    fields = [
        'name', 'category', 'description', 'makeready_price', 'price_per_sheet',
        'plate_price', 'base_waste_sheets', 'waste_percentage', 'makeready_time_minutes',
        'cleaning_time_minutes', 'sheets_per_minute', 'divides_quantity_by', 
        'multiplies_quantity_by', 'uses_colors', 'uses_front_colors_only', 'is_active'
    ]

    def post(self, request, *args, **kwargs):
        # Handle AJAX requests for inline operation creation
        if request.content_type == 'application/json':
            import json
            try:
                data = json.loads(request.body)
                
                # Check if operation with same name and category already exists
                if Operation.objects.filter(name=data['name'], category_id=data['category']).exists():
                    return JsonResponse({
                        'success': False,
                        'error': f'An operation named "{data["name"]}" already exists in this category. Please choose a different name.'
                    })
                
                # Create operation with provided data
                operation = Operation.objects.create(
                    name=data['name'],
                    category_id=data['category'],
                    description=data.get('description', ''),
                    makeready_price=data['makeready_price'],
                    price_per_sheet=data['price_per_sheet'],
                    plate_price=data.get('plate_price', 0),
                    uses_colors=data.get('uses_colors', False),
                    is_active=data.get('is_active', True),
                    # Set defaults for other fields
                    base_waste_sheets=0,
                    waste_percentage=0,
                    makeready_time_minutes=0,
                    cleaning_time_minutes=0,
                    sheets_per_minute=1,
                    divides_quantity_by=1,
                    multiplies_quantity_by=1,
                    uses_front_colors_only=False
                )
                
                return JsonResponse({
                    'success': True,
                    'operation_id': operation.id,
                    'operation_name': operation.name,
                    'message': f'Operation "{operation.name}" created successfully!'
                })
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Operation creation error: {error_details}")
                return JsonResponse({
                    'success': False,
                    'error': f'Error creating operation: {str(e)}'
                })
        
        # Handle regular form submission
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'Operation "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class OperationUpdateView(LoginRequiredMixin, UpdateView):
    """Update existing operation."""
    model = Operation
    template_name = 'operations/operation_form.html'
    fields = [
        'name', 'category', 'description', 'makeready_price', 'price_per_sheet',
        'plate_price', 'base_waste_sheets', 'waste_percentage', 'makeready_time_minutes',
        'cleaning_time_minutes', 'sheets_per_minute', 'divides_quantity_by', 
        'multiplies_quantity_by', 'uses_colors', 'uses_front_colors_only', 'is_active'
    ]

    def form_valid(self, form):
        messages.success(self.request, f'Operation "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class OperationDeleteView(LoginRequiredMixin, DeleteView):
    """Delete operation."""
    model = Operation
    template_name = 'operations/operation_confirm_delete.html'
    success_url = reverse_lazy('operations:list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.success(request, f'Operation "{self.object.name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)


# Category Views

class CategoryListView(LoginRequiredMixin, ListView):
    """List all operation categories."""
    model = OperationCategory
    template_name = 'operations/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return OperationCategory.objects.all().order_by('sort_order', 'name')


# Paper Type Views

class PaperTypeListView(LoginRequiredMixin, ListView):
    """List all paper types."""
    model = PaperType
    template_name = 'operations/papertype_list.html'
    context_object_name = 'paper_types'

    def get_queryset(self):
        return PaperType.objects.filter(is_active=True).order_by('name')


class PaperTypeCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    """Create new paper type."""
    model = PaperType
    template_name = 'operations/papertype_form.html'
    fields = ['name', 'weight_gsm', 'description', 'price_per_kg', 'is_active']
    success_url = reverse_lazy('operations:paper_types')

    def form_valid(self, form):
        messages.success(self.request, f'Paper type "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class PaperTypeUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    """Update existing paper type."""
    model = PaperType
    template_name = 'operations/papertype_form.html'
    fields = ['name', 'weight_gsm', 'description', 'price_per_kg', 'is_active']
    success_url = reverse_lazy('operations:paper_types')

    def form_valid(self, form):
        messages.success(self.request, f'Paper type "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class PaperTypeDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    """Delete paper type."""
    model = PaperType
    template_name = 'operations/papertype_confirm_delete.html'
    success_url = reverse_lazy('operations:paper_types')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.success(request, f'Paper type "{self.object.name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)


# Paper Size Views

class PaperSizeListView(LoginRequiredMixin, ListView):
    """List all paper sizes."""
    model = PaperSize
    template_name = 'operations/papersize_list.html'
    context_object_name = 'paper_sizes'

    def get_queryset(self):
        return PaperSize.objects.all().order_by('name')


class PaperSizeCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    """Create new paper size."""
    model = PaperSize
    template_name = 'operations/papersize_form.html'
    fields = ['name', 'width_cm', 'height_cm', 'description', 'is_standard', 'parent_size', 'parts_of_parent']
    success_url = reverse_lazy('operations:paper_sizes')

    def form_valid(self, form):
        messages.success(self.request, f'Paper size "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class PaperSizeUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    """Update existing paper size."""
    model = PaperSize
    template_name = 'operations/papersize_form.html'
    fields = ['name', 'width_cm', 'height_cm', 'description', 'is_standard', 'parent_size', 'parts_of_parent']
    success_url = reverse_lazy('operations:paper_sizes')

    def form_valid(self, form):
        messages.success(self.request, f'Paper size "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class PaperSizeDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    """Delete paper size."""
    model = PaperSize
    template_name = 'operations/papersize_confirm_delete.html'
    success_url = reverse_lazy('operations:paper_sizes')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.success(request, f'Paper size "{self.object.name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)


# Machine Views

# class MachineListView(LoginRequiredMixin, ListView):
#     """List all printing machines."""
#     model = PrintingMachine
#     template_name = 'operations/machine_list.html'
#     context_object_name = 'machines'
#
#     def get_queryset(self):
#         return PrintingMachine.objects.filter(is_active=True).order_by('name')


# API Views

def paper_size_parent_info(request, pk):
    """API endpoint to get parent size information for a paper size."""
    paper_size = get_object_or_404(PaperSize, pk=pk)
    
    parent_size = paper_size.get_parent_size_for_job()
    parts_of_parent = paper_size.get_parts_of_parent_for_job()
    
    return JsonResponse({
        'parent_size_id': parent_size.pk,
        'parent_size_name': parent_size.name,
        'parts_of_parent': parts_of_parent,
        'has_parent': paper_size.parent_size is not None
    })