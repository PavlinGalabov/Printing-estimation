"""
Models for printing operations and materials.
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
    Master operations that can be used in job calculations.
    """
    PRICING_TYPES = [
        ('per_piece', 'Per Piece'),
        ('per_weight', 'Per Weight (kg)'),
        ('per_sheet', 'Per Sheet'),
        ('per_color', 'Per Color'),
        ('outsourcing', 'Outsourcing (Fixed Rate)'),
        ('custom', 'Custom Formula'),
    ]

    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        OperationCategory,
        on_delete=models.CASCADE,
        related_name='operations'
    )
    description = models.TextField(blank=True)
    pricing_type = models.CharField(max_length=20, choices=PRICING_TYPES)

    # Pricing fields (usage depends on pricing_type)
    makeready_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Fixed setup cost"
    )
    price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Cost per piece/kg/sheet/color"
    )
    outsourcing_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Fixed outsourcing rate"
    )

    # Time calculations
    makeready_time_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Setup time in minutes"
    )
    time_per_unit_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Processing time per unit in seconds"
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

    # Custom formula (for advanced operations)
    custom_cost_formula = models.TextField(
        blank=True,
        help_text="Python expression for custom cost calculation"
    )
    custom_time_formula = models.TextField(
        blank=True,
        help_text="Python expression for custom time calculation"
    )

    is_active = models.BooleanField(default=True)
    requires_colors = models.BooleanField(
        default=False,
        help_text="Operation cost depends on number of colors"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category__sort_order', 'name']
        unique_together = ['name', 'category']

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    @property
    def makeready_time(self):
        """Return makeready time as timedelta."""
        return timedelta(minutes=self.makeready_time_minutes)

    @property
    def time_per_unit(self):
        """Return time per unit as timedelta."""
        return timedelta(seconds=self.time_per_unit_seconds)


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


class PrintingMachine(models.Model):
    """
    Printing machines with specifications and pricing.
    """
    name = models.CharField(max_length=100, unique=True)
    max_paper_width_cm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(1)]
    )
    max_paper_height_cm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(1)]
    )
    max_colors = models.PositiveIntegerField(default=4)
    cost_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Operating cost per hour"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (max: {self.max_paper_width_cm}×{self.max_paper_height_cm}cm)"

    def can_handle_size(self, width_cm, height_cm):
        """Check if machine can handle given paper size."""
        return (width_cm <= self.max_paper_width_cm and
                height_cm <= self.max_paper_height_cm)