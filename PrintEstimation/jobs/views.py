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
from .models import Job, JobOperation, JobVariant
from .forms import JobForm, JobOperationForm
from PrintEstimation.accounts.models import Client
from PrintEstimation.operations.models import Operation


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view."""
    template_name = 'jobs/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get user's recent jobs
        context['recent_jobs'] = Job.objects.filter(
            created_by=self.request.user,
            is_template=False
        ).order_by('-created_at')[:10]

        # Get statistics
        context.update({
            'total_jobs': Job.objects.filter(created_by=self.request.user, is_template=False).count(),
            'total_templates': Job.objects.filter(created_by=self.request.user, is_template=True).count(),
            'pending_jobs': Job.objects.filter(created_by=self.request.user, status='draft').count(),
            'sent_jobs': Job.objects.filter(created_by=self.request.user, status='sent').count(),
        })

        return context


class JobListView(LoginRequiredMixin, ListView):
    """List all jobs (non-templates)."""
    model = Job
    template_name = 'jobs/job_list.html'
    context_object_name = 'jobs'
    paginate_by = 20

    def get_queryset(self):
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
    template_name = 'jobs/job_detail.html'
    context_object_name = 'job'

    def get_queryset(self):
        return Job.objects.filter(created_by=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get job operations in order
        context['job_operations'] = self.object.job_operations.all().order_by('sequence_order')

        # Get quantity variants
        context['variants'] = self.object.variants.all().order_by('quantity')

        return context


class JobCreateView(LoginRequiredMixin, CreateView):
    """Create new job."""
    model = Job
    form_class = JobForm
    template_name = 'jobs/job_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['operations'] = Operation.objects.filter(is_active=True)
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'Job "{form.instance.order_name}" created successfully!')
        return super().form_valid(form)


class JobUpdateView(LoginRequiredMixin, UpdateView):
    """Update existing job."""
    model = Job
    form_class = JobForm
    template_name = 'jobs/job_form.html'

    def get_queryset(self):
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
        return Job.objects.filter(created_by=self.request.user)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.success(request, f'Job "{self.object.order_name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)


class JobCalculateView(LoginRequiredMixin, DetailView):
    """Calculate job costs and generate breakdown."""
    model = Job
    template_name = 'jobs/job_calculate.html'

    def get_queryset(self):
        return Job.objects.filter(created_by=self.request.user)

    def post(self, request, *args, **kwargs):
        """Handle calculation request."""
        job = self.get_object()

        # TODO: Implement calculation logic here
        # For now, just update status
        job.status = 'calculated'
        job.save()

        messages.success(request, 'Job calculated successfully!')
        return self.get(request, *args, **kwargs)


class TemplateListView(LoginRequiredMixin, ListView):
    """List all templates."""
    model = Job
    template_name = 'jobs/template_list.html'
    context_object_name = 'templates'
    paginate_by = 20

    def get_queryset(self):
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