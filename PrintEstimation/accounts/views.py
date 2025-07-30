"""
Views for accounts app - user and client management.
"""

from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, ListView, DetailView, UpdateView, DeleteView, TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from .models import User, Client
from .forms import ClientForm, CustomUserCreationForm


class SuperuserRequiredMixin(UserPassesTestMixin):
    """Mixin to require superuser access."""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser_type


class RegisterView(CreateView):
    """User registration view."""
    model = User
    form_class = CustomUserCreationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        messages.success(self.request, 'Account created successfully! You can now log in.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class ProfileView(LoginRequiredMixin, TemplateView):
    """User profile view."""
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get job statistics for the user
        try:
            from django.apps import apps
            Job = apps.get_model('jobs', 'Job')
            
            user_jobs = Job.objects.filter(created_by=self.request.user)
            context.update({
                'total_jobs': user_jobs.count(),
                'draft_jobs': user_jobs.filter(status='draft').count(),
                'calculated_jobs': user_jobs.filter(status='calculated').count(),
                'sent_jobs': user_jobs.filter(status='sent').count(),
            })
        except Exception:
            # If there's any import error, set default values
            context.update({
                'total_jobs': 0,
                'draft_jobs': 0,
                'calculated_jobs': 0,
                'sent_jobs': 0,
            })
        
        return context

    def post(self, request, *args, **kwargs):
        """Handle profile update."""
        if request.content_type == 'application/json':
            import json
            try:
                data = json.loads(request.body)
                user = request.user
                
                # Update allowed fields
                user.email = data.get('email', user.email)
                user.first_name = data.get('first_name', user.first_name)
                user.last_name = data.get('last_name', user.last_name)
                user.phone = data.get('phone', user.phone)
                
                user.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Profile updated successfully!'
                })
                
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })
        
        # Handle regular form submission
        user = request.user
        user.email = request.POST.get('email', user.email)
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.phone = request.POST.get('phone', user.phone)
        
        try:
            user.save()
            messages.success(request, 'Profile updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
        
        return self.get(request, *args, **kwargs)


class PasswordChangeView(LoginRequiredMixin, TemplateView):
    """Handle password change requests."""
    
    def post(self, request, *args, **kwargs):
        """Handle password change."""
        from django.contrib.auth import authenticate, update_session_auth_hash
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        
        if request.content_type == 'application/json':
            import json
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid JSON data'
                })
        else:
            data = request.POST
        
        old_password = data.get('old_password')
        new_password1 = data.get('new_password1')
        new_password2 = data.get('new_password2')
        
        # Validate required fields
        if not all([old_password, new_password1, new_password2]):
            return JsonResponse({
                'success': False,
                'error': 'All password fields are required'
            })
        
        # Check if new passwords match
        if new_password1 != new_password2:
            return JsonResponse({
                'success': False,
                'error': 'New passwords do not match'
            })
        
        # Authenticate current password
        user = authenticate(username=request.user.username, password=old_password)
        if not user:
            return JsonResponse({
                'success': False,
                'error': 'Current password is incorrect'
            })
        
        # Validate new password
        try:
            validate_password(new_password1, user)
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': '; '.join(e.messages)
            })
        
        # Change password
        try:
            user.set_password(new_password1)
            user.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            
            return JsonResponse({
                'success': True,
                'message': 'Password changed successfully!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error changing password: {str(e)}'
            })


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
        try:
            context['recent_jobs'] = self.object.jobs.all()[:5]
        except Exception:
            # If there's any import error, set empty list
            context['recent_jobs'] = []
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