"""
PDF export service for jobs using HTML templates.
Since external PDF libraries aren't available, we'll use HTML responses that can be printed to PDF.
"""

import os
from datetime import datetime
from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.http import HttpResponse
from .models import Job, JobPDFExport


class JobPDFGenerator:
    """Generate printable HTML exports for jobs."""
    
    def __init__(self, job):
        self.job = job
    
    def generate_estimate_html(self):
        """Generate estimate/quote HTML content."""
        # Calculate cost per piece
        cost_per_piece = 0
        if self.job.total_cost and self.job.quantity > 0:
            cost_per_piece = float(self.job.total_cost) / self.job.quantity
        
        # Calculate operations cost (total material cost minus paper cost)
        operations_cost = 0
        if self.job.total_material_cost and self.job.paper_cost:
            operations_cost = float(self.job.total_material_cost) - float(self.job.paper_cost)
        
        context = {
            'job': self.job,
            'operations': self.job.job_operations.all().order_by('sequence_order'),
            'generated_at': datetime.now(),
            'export_type': 'estimate',
            'cost_per_piece': cost_per_piece,
            'operations_cost': operations_cost
        }
        
        html_content = render_to_string('jobs/pdf_templates/estimate.html', context)
        return html_content
    
    def generate_job_sheet_html(self):
        """Generate production job sheet HTML content."""
        context = {
            'job': self.job,
            'operations': self.job.job_operations.all().order_by('sequence_order'),
            'generated_at': datetime.now(),
            'export_type': 'job_sheet'
        }
        
        html_content = render_to_string('jobs/pdf_templates/job_sheet.html', context)
        return html_content


class PDFExportService:
    """Service for managing HTML exports that can be printed as PDF."""
    
    @staticmethod
    def create_export(job, export_type, user):
        """Create an HTML export for a job."""
        generator = JobPDFGenerator(job)
        
        if export_type == 'estimate':
            html_content = generator.generate_estimate_html()
            filename = f"estimate_{job.job_number or job.pk}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        elif export_type == 'job_sheet':
            html_content = generator.generate_job_sheet_html()
            filename = f"jobsheet_{job.job_number or job.pk}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        else:
            raise ValueError(f"Unsupported export type: {export_type}")
        
        # Create the export record
        export = JobPDFExport.objects.create(
            job=job,
            export_type=export_type,
            file_name=filename,
            created_by=user,
            file_size=len(html_content.encode('utf-8'))
        )
        
        # Save the HTML file
        export.file_path.save(
            filename,
            ContentFile(html_content.encode('utf-8')),
            save=True
        )
        
        return export, html_content
    
    @staticmethod
    def get_export_history(job=None, user=None):
        """Get export history with optional filters."""
        queryset = JobPDFExport.objects.all()
        
        if job:
            queryset = queryset.filter(job=job)
        if user:
            queryset = queryset.filter(created_by=user)
        
        return queryset.order_by('-created_at')