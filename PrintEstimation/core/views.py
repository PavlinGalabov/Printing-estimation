"""
Core views for the printing estimation system.
"""

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from PrintEstimation.jobs.models import Job
from PrintEstimation.accounts.models import Client


class HomeView(TemplateView):
    """
    Home page view - public landing page.
    """
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add dashboard data for authenticated users
        if self.request.user.is_authenticated:
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

            context.update({
                # Workflow job lists
                'urgent_jobs': urgent_jobs,
                'approved_jobs': approved_jobs,
                'waiting_manager_jobs': waiting_manager_jobs,
                'waiting_client_jobs': waiting_client_jobs,
                
                # Counts for the cards
                'urgent_count': urgent_jobs.count(),
                'approved_count': approved_jobs.count(),
                'waiting_manager_count': waiting_manager_jobs.count(),
                'waiting_client_count': waiting_client_jobs.count(),
            })

        return context


class AboutView(TemplateView):
    """
    About page view.
    """
    template_name = 'core/about.html'