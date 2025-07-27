"""
Models for printing operations with simplified formula-based approach.
Each operation contains its own constants and formulas.
"""

from datetime import timedelta
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _


class OperationCategory(models.Model):
    """
    Categories for organizing operations (Cutting, Printing, Finishing, etc.)
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=7,
        default='#007bff',
        help_text="Hex color code for UI display"
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Operation Category'
        verbose_name_plural = 'Operation Categories'

    def __str__(self):
        return self.name


class Operation(models.Model):
    """
    Master operations with built-in formulas and constants.
    Each operation is specific (e.g., "Color Printing Quarter Size").
    """
    name = models.CharField(
        max_length=150,
        help_text="Specific operation name (e.g., 'Color Printing Quarter Size')"
    )
    category = models.ForeignKey(
        OperationCategory,
        on_delete=models.CASCADE,
        related_name='operations'
    )
    description = models.TextField(blank=True)

    # Cost Formula Constants
    makeready_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Fixed setup cost (e.g., 10.00)"
    )
    price_per_sheet = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Cost per sheet processed (e.g., 0.005)"
    )

    # Additional cost constants (for operations like printing)
    plate_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Cost per plate/color (for printing operations)"
    )

    # Waste calculation constants
    base_waste_sheets = models.PositiveIntegerField(
        default=0,
        help_text="Base waste sheets (e.g., 30 for printing)"
    )
    waste_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
        help_text="Waste percentage per sheet (e.g., 0.0001 for 0.01%)"
    )

    # Time Formula Constants
    makeready_time_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Setup time in minutes (e.g., 15)"
    )
    cleaning_time_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Cleaning time per color in minutes (e.g., 20)"
    )
    sheets_per_minute = models.PositiveIntegerField(
        default=1,
        help_text="Processing speed (sheets per minute, e.g., 80)"
    )

    # Quantity effects
    divides_quantity_by = models.PositiveIntegerField(
        default=1,
        help_text="Divide current quantity by this number (for cutting operations)"
    )
    multiplies_quantity_by = models.PositiveIntegerField(
        default=1,
        help_text="Multiply current quantity by this number"
    )

    # Operation behavior
    uses_colors = models.BooleanField(
        default=False,
        help_text="Operation cost/time depends on number of colors"
    )
    uses_front_colors_only = models.BooleanField(
        default=False,
        help_text="Uses only front colors for cleaning time calculation"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category__sort_order', 'name']
        unique_together = ['name', 'category']

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    def calculate_cost(self, job_params, operation_parameters=None):
        """
        Calculate cost for this operation based on job parameters.

        Args:
            job_params: dict with keys like:
                - quantity: int
                - n_up: int
                - colors_front: int
                - colors_back: int
                - current_quantity: int (sheets going into this operation)
            operation_parameters: dict with dynamic parameters (e.g., {'cut_pieces': 4})

        Returns:
            dict with 'total_cost', 'waste_sheets', 'quantity_after'
        """
        operation_parameters = operation_parameters or {}
        current_quantity = job_params.get('current_quantity', job_params['quantity'])

        # Calculate waste sheets if this operation generates waste
        # Waste should be calculated based on print_run (sheets), not current_quantity
        print_run = job_params['print_run']
        waste_sheets = 0
        if self.base_waste_sheets > 0 or self.waste_percentage > 0:
            if self.uses_colors:
                total_colors = job_params['colors_front'] + job_params['colors_back']
                waste_sheets = total_colors * (
                    self.base_waste_sheets +
                    float(self.waste_percentage) * print_run
                )
            else:
                waste_sheets = (
                    self.base_waste_sheets +
                    float(self.waste_percentage) * print_run
                )
            waste_sheets = int(waste_sheets)

        # Calculate processing quantity (including waste)
        processing_quantity = current_quantity + waste_sheets

        # Calculate cost
        if self.uses_colors:
            # For printing operations - each color requires makeready, plate, and processing
            total_colors = job_params['colors_front'] + job_params['colors_back']
            total_cost = total_colors * (
                float(self.makeready_price) +
                float(self.plate_price) +
                processing_quantity * float(self.price_per_sheet)
            )
        else:
            # For other operations - single makeready + processing
            base_cost = float(self.makeready_price) + processing_quantity * float(self.price_per_sheet)
            
            # Apply cut pricing multiplier if this is a cutting operation
            if 'cut_pieces' in operation_parameters:
                cut_pieces = operation_parameters['cut_pieces']
                # Price = makeready + (processing_quantity × price_per_sheet × number_of_cuts)
                total_cost = float(self.makeready_price) + processing_quantity * float(self.price_per_sheet) * cut_pieces
            else:
                total_cost = base_cost

        # Calculate quantity after this operation (subtract waste, then apply multipliers/dividers)
        quantity_after = current_quantity - waste_sheets
        
        # Apply dynamic parameters first (e.g., cut_pieces)
        if 'cut_pieces' in operation_parameters:
            quantity_after = quantity_after * operation_parameters['cut_pieces']
        elif 'divide_by' in operation_parameters:
            quantity_after = quantity_after // operation_parameters['divide_by']
        else:
            # Use static operation settings as fallback
            if self.divides_quantity_by > 1:
                quantity_after = quantity_after // self.divides_quantity_by
            elif self.multiplies_quantity_by > 1:
                quantity_after = quantity_after * self.multiplies_quantity_by

        return {
            'total_cost': total_cost,
            'waste_sheets': waste_sheets,
            'processing_quantity': processing_quantity,
            'quantity_after': quantity_after
        }

    def calculate_time(self, job_params, operation_parameters=None):
        """
        Calculate time for this operation based on job parameters.

        Args:
            operation_parameters: dict with dynamic parameters (e.g., {'cut_pieces': 4})

        Returns:
            int: total time in minutes
        """
        operation_parameters = operation_parameters or {}
        current_quantity = job_params.get('current_quantity', job_params['quantity'])

        # Calculate waste and processing quantity (same as cost calculation)
        # Use print_run for waste calculation, not current_quantity
        print_run = job_params['print_run']
        waste_sheets = 0
        if self.base_waste_sheets > 0 or self.waste_percentage > 0:
            if self.uses_colors:
                total_colors = job_params['colors_front'] + job_params['colors_back']
                waste_sheets = total_colors * (
                    self.base_waste_sheets +
                    float(self.waste_percentage) * print_run
                )
            else:
                waste_sheets = (
                    self.base_waste_sheets +
                    float(self.waste_percentage) * print_run
                )
            waste_sheets = int(waste_sheets)

        processing_quantity = current_quantity + waste_sheets

        # Calculate time
        total_time = self.makeready_time_minutes

        if self.uses_colors:
            # Add cleaning time
            if self.uses_front_colors_only:
                cleaning_colors = job_params['colors_front']
            else:
                total_colors = job_params['colors_front'] + job_params['colors_back']
                cleaning_colors = total_colors

            total_time += cleaning_colors * self.cleaning_time_minutes

            # Add processing time per color
            if self.sheets_per_minute > 0:
                total_colors = job_params['colors_front'] + job_params['colors_back']
                total_time += total_colors * (processing_quantity / self.sheets_per_minute)
        else:
            # Add processing time
            if self.sheets_per_minute > 0:
                total_time += processing_quantity / self.sheets_per_minute

        return int(total_time)

    def get_absolute_url(self):
        """Return URL for operation detail view."""
        from django.urls import reverse
        return reverse('operations:detail', kwargs={'pk': self.pk})


class PaperType(models.Model):
    """
    Paper types with specifications and pricing.
    """
    name = models.CharField(max_length=100, unique=True)
    weight_gsm = models.PositiveIntegerField(
        help_text="Weight in grams per square meter"
    )
    price_per_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Price per kilogram"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.weight_gsm}gsm)"


class PaperSize(models.Model):
    """
    Standard paper sizes used in printing.
    """
    name = models.CharField(max_length=50, unique=True)
    width_cm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0.1)]
    )
    height_cm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0.1)]
    )
    description = models.CharField(max_length=200, blank=True)
    is_standard = models.BooleanField(
        default=False,
        help_text="Standard industry size (A4, A3, etc.)"
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.width_cm} × {self.height_cm} cm)"

    @property
    def area_m2(self):
        """Calculate area in square meters."""
        return float(self.width_cm * self.height_cm) / 10000

    @property
    def area_cm2(self):
        """Calculate area in square centimeters."""
        return float(self.width_cm * self.height_cm)