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
            'notes', 'variant_quantities'
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
            'variant_quantities': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'e.g., 2000,5000,10000'}),
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
        self.fields['variant_quantities'].help_text = "Additional quantities for pricing (comma-separated)"

        # Make book-specific fields conditional
        self.fields['number_of_pages'].required = False
        self.fields['n_up_signatures'].required = False

    def clean_variant_quantities(self):
        """Validate variant quantities format."""
        value = self.cleaned_data.get('variant_quantities', '')
        if not value:
            return value

        try:
            quantities = [int(q.strip()) for q in value.split(',') if q.strip()]
            if len(quantities) > 5:
                raise ValidationError("Maximum 5 variant quantities allowed.")
            if any(q <= 0 for q in quantities):
                raise ValidationError("All quantities must be positive numbers.")
            return ','.join(map(str, quantities))
        except ValueError:
            raise ValidationError("Please enter comma-separated numbers (e.g., 2000,5000,10000)")

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


class ClientForm(forms.ModelForm):
    """Form for creating and editing clients."""

    class Meta:
        model = Client
        fields = [
            'company_name', 'contact_person', 'email', 'phone', 'mobile',
            'website', 'address_line_1', 'address_line_2', 'city',
            'state_province', 'postal_code', 'country', 'tax_number',
            'payment_terms', 'credit_limit', 'discount_percentage',
            'notes', 'special_requirements', 'is_vip'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'address_line_1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state_province': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_number': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_terms': forms.Select(attrs={'class': 'form-select'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount_percentage': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'special_requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_vip': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }