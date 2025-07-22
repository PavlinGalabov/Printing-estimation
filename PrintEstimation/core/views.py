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

        # Add basic statistics for the homepage
        if self.request.user.is_authenticated:
            context.update({
                'total_jobs': Job.objects.filter(is_template=False).count(),
                'total_templates': Job.objects.filter(is_template=True).count(),
                'total_clients': Client.objects.filter(is_active=True).count(),
            })

        return context


class AboutView(TemplateView):
    """
    About page view.
    """
    template_name = 'core/about.html'