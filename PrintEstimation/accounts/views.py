"""
Views for accounts app - user and client management.
"""

from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, ListView, DetailView, UpdateView, DeleteView, TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .models import User, Client
from PrintEstimation.jobs.forms import ClientForm


class SuperuserRequiredMixin(UserPassesTestMixin):
    """Mixin to require superuser access."""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser_type


class RegisterView(CreateView):
    """User registration view."""
    model = User
    form_class = UserCreationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        messages.success(self.request, 'Account created successfully! You can now log in.')
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, TemplateView):
    """User profile view."""
    template_name = 'accounts/profile.html'


# Client Management Views

class ClientListView(LoginRequiredMixin, ListView):
    """List all clients."""
    model = Client
    template_name = 'accounts/client_list.html'
    context_object_name = 'clients'
    paginate_by = 20

    def get_queryset(self):
        queryset = Client.objects.filter(is_active=True)
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                company_name__icontains=search
            )
        return queryset.order_by('company_name')


class ClientDetailView(LoginRequiredMixin, DetailView):
    """Client detail view."""
    model = Client
    template_name = 'accounts/client_detail.html'
    context_object_name = 'client'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add recent jobs for this client
        context['recent_jobs'] = self.object.jobs.all()[:5]
        return context


class ClientCreateView(LoginRequiredMixin, CreateView):
    """Create new client."""
    model = Client
    form_class = ClientForm
    template_name = 'accounts/client_form.html'

    def form_valid(self, form):
        messages.success(self.request, f'Client "{form.instance.company_name}" created successfully!')
        return super().form_valid(form)


class ClientUpdateView(LoginRequiredMixin, UpdateView):
    """Update existing client."""
    model = Client
    form_class = ClientForm
    template_name = 'accounts/client_form.html'

    def form_valid(self, form):
        messages.success(self.request, f'Client "{form.instance.company_name}" updated successfully!')
        return super().form_valid(form)


class ClientDeleteView(LoginRequiredMixin, DeleteView):
    """Delete client (soft delete by setting inactive)."""
    model = Client
    template_name = 'accounts/client_confirm_delete.html'
    success_url = reverse_lazy('accounts:client_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Soft delete - just mark as inactive
        self.object.is_active = False
        self.object.save()
        messages.success(request, f'Client "{self.object.company_name}" deactivated successfully!')
        return super().delete(request, *args, **kwargs)