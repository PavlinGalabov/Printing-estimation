"""
Forms for job creation and management.
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import Job, JobOperation, JobVariant
from PrintEstimation.accounts.models import Client
from PrintEstimation.operations.models import Operation, PaperType, PaperSize


class JobForm(forms.ModelForm):
    """Form for creating and editing jobs."""

    class Meta:
        model = Job
        fields = [
            'client', 'order_type', 'order_name', 'quantity', 'deadline',
            'paper_type', 'end_size', 'custom_end_width', 'custom_end_height',
            'printing_size', 'selling_size', 'parts_of_selling_size', 'n_up', 
            'colors_front', 'colors_back', 'special_colors', 'number_of_pages', 
            'n_up_signatures', 'notes', 'is_template', 'template_name'
        ]
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select'}),
            'order_type': forms.Select(attrs={'class': 'form-select'}),
            'order_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter order name'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'paper_type': forms.Select(attrs={'class': 'form-select'}),
            'end_size': forms.Select(attrs={'class': 'form-select'}),
            'custom_end_width': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Width (cm)'}),
            'custom_end_height': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Height (cm)'}),
            'printing_size': forms.Select(attrs={'class': 'form-select'}),
            'selling_size': forms.Select(attrs={'class': 'form-select'}),
            'parts_of_selling_size': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'deadline': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
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
        
        # If printing_size is selected and has parent, auto-populate selling fields
        if self.instance and self.instance.pk and self.instance.printing_size:
            printing_size = self.instance.printing_size
            parent_size = printing_size.get_parent_size_for_job()
            parts_of_parent = printing_size.get_parts_of_parent_for_job()
            
            if not self.instance.selling_size:
                self.instance.selling_size = parent_size
            if not self.instance.parts_of_selling_size or self.instance.parts_of_selling_size == 1:
                self.instance.parts_of_selling_size = parts_of_parent

        # Add help text
        self.fields['parts_of_selling_size'].help_text = "How many printing sheets fit in one parent sheet"
        self.fields['n_up'].help_text = "Number of items per printing sheet"

        # Make book-specific fields conditional
        self.fields['number_of_pages'].required = False
        self.fields['n_up_signatures'].required = False
        
        # Make template fields conditional
        self.fields['template_name'].required = False
        
        # Make end size flexible (either standard or custom)
        self.fields['end_size'].required = False
        self.fields['custom_end_width'].required = False
        self.fields['custom_end_height'].required = False


    def clean(self):
        """Additional form validation."""
        cleaned_data = super().clean()
        order_type = cleaned_data.get('order_type')
        number_of_pages = cleaned_data.get('number_of_pages')
        n_up_signatures = cleaned_data.get('n_up_signatures')
        end_size = cleaned_data.get('end_size')
        custom_end_width = cleaned_data.get('custom_end_width')
        custom_end_height = cleaned_data.get('custom_end_height')

        # Validate book-specific fields
        if order_type == 'book':
            if not number_of_pages:
                self.add_error('number_of_pages', 'Number of pages is required for books.')
            if not n_up_signatures:
                self.add_error('n_up_signatures', 'N-up signatures is required for books.')

        # Validate end size: either standard size OR custom dimensions (both width and height)
        has_standard_size = bool(end_size)
        has_custom_size = bool(custom_end_width and custom_end_height)
        
        if not has_standard_size and not has_custom_size:
            self.add_error('end_size', 'Please select a standard size or enter custom dimensions.')
            self.add_error('custom_end_width', 'Enter both width and height for custom size.')
            self.add_error('custom_end_height', 'Enter both width and height for custom size.')
        elif has_custom_size and has_standard_size:
            self.add_error('end_size', 'Please use either standard size OR custom dimensions, not both.')
        elif custom_end_width and not custom_end_height:
            self.add_error('custom_end_height', 'Height is required when width is specified.')
        elif custom_end_height and not custom_end_width:
            self.add_error('custom_end_width', 'Width is required when height is specified.')

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


class JobStatusChangeForm(forms.ModelForm):
    """Form for changing job status without JavaScript."""
    
    class Meta:
        model = Job
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].label = 'Change Status To'


class JobCalculationForm(forms.Form):
    """Form for triggering job calculations."""
    
    action = forms.CharField(widget=forms.HiddenInput(), initial='calculate')


class AddOperationForm(forms.Form):
    """Form for adding an operation to a job."""
    
    operation = forms.ModelChoiceField(
        queryset=Operation.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select an operation to add..."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Group operations by category for better UX
        self.fields['operation'].queryset = Operation.objects.filter(
            is_active=True
        ).select_related('category').order_by('category__sort_order', 'name')


class AddOperationAfterForm(forms.Form):
    """Form for adding an operation after a specific position."""
    
    operation = forms.ModelChoiceField(
        queryset=Operation.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        empty_label="Select operation to add..."
    )
    after_operation_id = forms.IntegerField(widget=forms.HiddenInput())
    operation_parameters = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Group operations by category for better UX
        self.fields['operation'].queryset = Operation.objects.filter(
            is_active=True
        ).select_related('category').order_by('category__sort_order', 'name')
        
    def clean_operation_parameters(self):
        """Parse JSON parameters if provided."""
        params_str = self.cleaned_data.get('operation_parameters', '')
        if params_str:
            try:
                import json
                return json.loads(params_str)
            except json.JSONDecodeError:
                return {}
        return {}


class RemoveOperationForm(forms.Form):
    """Form for removing an operation from a job."""
    
    operation_id = forms.IntegerField(widget=forms.HiddenInput())
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="I confirm I want to remove this operation"
    )


class ReorderOperationsForm(forms.Form):
    """Form for reordering operations."""
    
    # Fields for each operation ID and its new sequence order
    def __init__(self, *args, **kwargs):
        job = kwargs.pop('job', None)
        super().__init__(*args, **kwargs)
        
        if job:
            operations = job.job_operations.all().order_by('sequence_order')
            for op in operations:
                field_name = f'operation_{op.id}_order'
                self.fields[field_name] = forms.IntegerField(
                    min_value=1,
                    max_value=operations.count(),
                    initial=op.sequence_order,
                    widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
                    label=f'{op.operation_name} - Order'
                )


class JobVariantForm(forms.ModelForm):
    """Form for creating/editing individual job variants."""
    
    class Meta:
        model = JobVariant
        fields = ['quantity']
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Enter quantity (e.g. 1000)'
            })
        }
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity and quantity < 1:
            raise ValidationError("Quantity must be at least 1.")
        return quantity


class MultiQuantityForm(forms.Form):
    """Form for adding multiple quantity variants at once."""
    
    quantities = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter quantities separated by commas\nExample: 500, 1000, 2000, 5000'
        }),
        help_text="Enter quantities separated by commas (e.g., 500, 1000, 2000, 5000)"
    )
    
    def clean_quantities(self):
        """Parse and validate quantities."""
        quantities_str = self.cleaned_data.get('quantities', '')
        if not quantities_str.strip():
            raise ValidationError("Please enter at least one quantity.")
        
        quantities = []
        for qty_str in quantities_str.split(','):
            qty_str = qty_str.strip()
            if not qty_str:
                continue
            try:
                qty = int(qty_str)
                if qty < 1:
                    raise ValidationError(f"Quantity {qty} must be at least 1.")
                if qty in quantities:
                    raise ValidationError(f"Duplicate quantity: {qty}")
                quantities.append(qty)
            except ValueError:
                raise ValidationError(f"'{qty_str}' is not a valid number.")
        
        if not quantities:
            raise ValidationError("Please enter at least one valid quantity.")
        
        if len(quantities) > 20:
            raise ValidationError("Maximum 20 quantity variants allowed.")
        
        return sorted(quantities)


class CalculateVariantsForm(forms.Form):
    """Form for triggering variant calculations."""
    
    calculate_all = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Recalculate all existing variants"
    )
    
    def __init__(self, *args, **kwargs):
        self.job = kwargs.pop('job', None)
        super().__init__(*args, **kwargs)


