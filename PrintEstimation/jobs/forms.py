"""
Forms for job creation and management.
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import Job, JobOperation
from PrintEstimation.accounts.models import Client
from PrintEstimation.operations.models import Operation, PaperType, PaperSize


class JobForm(forms.ModelForm):
    """Form for creating and editing jobs."""

    class Meta:
        model = Job
        fields = [
            'client', 'order_type', 'order_name', 'quantity',
            'paper_type', 'end_size', 'printing_size', 'selling_size',
            'parts_of_selling_size', 'n_up', 'colors_front', 'colors_back',
            'special_colors', 'number_of_pages', 'n_up_signatures',
            'notes', 'is_template', 'template_name'
        ]
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select'}),
            'order_type': forms.Select(attrs={'class': 'form-select'}),
            'order_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter order name'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'paper_type': forms.Select(attrs={'class': 'form-select'}),
            'end_size': forms.Select(attrs={'class': 'form-select'}),
            'printing_size': forms.Select(attrs={'class': 'form-select'}),
            'selling_size': forms.Select(attrs={'class': 'form-select'}),
            'parts_of_selling_size': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'n_up': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'colors_front': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '12'}),
            'colors_back': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '12'}),
            'special_colors': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'number_of_pages': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'n_up_signatures': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                           'placeholder': 'Client remarks, agreements, special requirements...'}),
            'is_template': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'template_name': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Enter template name'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter active clients
        self.fields['client'].queryset = Client.objects.filter(is_active=True)

        # Filter active paper types and sizes
        self.fields['paper_type'].queryset = PaperType.objects.filter(is_active=True)
        self.fields['end_size'].queryset = PaperSize.objects.all()
        self.fields['printing_size'].queryset = PaperSize.objects.all()
        self.fields['selling_size'].queryset = PaperSize.objects.all()

        # Add help text
        self.fields['parts_of_selling_size'].help_text = "How many printing sheets fit in one purchased sheet"
        self.fields['n_up'].help_text = "Number of items per printing sheet"

        # Make book-specific fields conditional
        self.fields['number_of_pages'].required = False
        self.fields['n_up_signatures'].required = False
        
        # Make template fields conditional
        self.fields['template_name'].required = False


    def clean(self):
        """Additional form validation."""
        cleaned_data = super().clean()
        order_type = cleaned_data.get('order_type')
        number_of_pages = cleaned_data.get('number_of_pages')
        n_up_signatures = cleaned_data.get('n_up_signatures')

        # Validate book-specific fields
        if order_type == 'book':
            if not number_of_pages:
                self.add_error('number_of_pages', 'Number of pages is required for books.')
            if not n_up_signatures:
                self.add_error('n_up_signatures', 'N-up signatures is required for books.')

        return cleaned_data

    def clean_template_name(self):
        """Validate template name if is_template is checked."""
        template_name = self.cleaned_data.get('template_name')
        is_template = self.cleaned_data.get('is_template')
        
        if is_template and not template_name:
            raise ValidationError("Template name is required when saving as template.")
        
        return template_name


class JobOperationForm(forms.ModelForm):
    """Form for adding operations to a job."""

    class Meta:
        model = JobOperation
        fields = ['operation', 'sequence_order']
        widgets = {
            'operation': forms.Select(attrs={'class': 'form-select'}),
            'sequence_order': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }

    def __init__(self, *args, **kwargs):
        job = kwargs.pop('job', None)
        super().__init__(*args, **kwargs)

        # Filter active operations
        self.fields['operation'].queryset = Operation.objects.filter(is_active=True)

        # Set default sequence order
        if job:
            next_order = job.job_operations.count() + 1
            self.initial['sequence_order'] = next_order
