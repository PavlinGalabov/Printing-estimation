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
from .models import (
    Operation, OperationCategory, PaperType,
    PaperSize,
)


class SuperuserRequiredMixin(UserPassesTestMixin):
    """Mixin to require superuser access."""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser_type


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


class OperationCreateView(SuperuserRequiredMixin, CreateView):
    """Create new operation."""
    model = Operation
    template_name = 'operations/operation_form.html'
    fields = [
        'name', 'category', 'description', 'pricing_type', 'makeready_price',
        'price_per_unit', 'outsourcing_rate', 'makeready_time_minutes',
        'time_per_unit_seconds', 'divides_quantity_by', 'multiplies_quantity_by',
        'requires_colors', 'is_active'
    ]

    def form_valid(self, form):
        messages.success(self.request, f'Operation "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class OperationUpdateView(SuperuserRequiredMixin, UpdateView):
    """Update existing operation."""
    model = Operation
    template_name = 'operations/operation_form.html'
    fields = [
        'name', 'category', 'description', 'pricing_type', 'makeready_price',
        'price_per_unit', 'outsourcing_rate', 'makeready_time_minutes',
        'time_per_unit_seconds', 'divides_quantity_by', 'multiplies_quantity_by',
        'requires_colors', 'is_active'
    ]

    def form_valid(self, form):
        messages.success(self.request, f'Operation "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class OperationDeleteView(SuperuserRequiredMixin, DeleteView):
    """Delete operation."""
    model = Operation
    template_name = 'operations/operation_confirm_delete.html'
    success_url = reverse_lazy('operations:list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.success(request, f'Operation "{self.object.name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)


# Category Views

class CategoryListView(SuperuserRequiredMixin, ListView):
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
    template_name = 'operations/paper_type_list.html'
    context_object_name = 'paper_types'

    def get_queryset(self):
        return PaperType.objects.filter(is_active=True).order_by('name')


# Paper Size Views

class PaperSizeListView(LoginRequiredMixin, ListView):
    """List all paper sizes."""
    model = PaperSize
    template_name = 'operations/paper_size_list.html'
    context_object_name = 'paper_sizes'

    def get_queryset(self):
        return PaperSize.objects.all().order_by('name')


# Machine Views

# class MachineListView(LoginRequiredMixin, ListView):
#     """List all printing machines."""
#     model = PrintingMachine
#     template_name = 'operations/machine_list.html'
#     context_object_name = 'machines'
#
#     def get_queryset(self):
#         return PrintingMachine.objects.filter(is_active=True).order_by('name')