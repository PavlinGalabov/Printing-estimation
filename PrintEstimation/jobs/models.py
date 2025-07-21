"""
Models for jobs, estimates, and calculations.
"""

from datetime import timedelta
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from django.urls import reverse
from PrintEstimation.operations.models import Operation, PaperType, PaperSize, PrintingMachine

User = get_user_model()


class Job(models.Model):
    """
    Main model representing both estimates and templates.
    Contains all parameters needed for printing estimation.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('sent', 'Sent to Client'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('archived', 'Archived'),
    ]

    ORDER_TYPES = [
        ('book', 'Book'),
        ('box', 'Box'),
        ('poster', 'Poster'),
        ('flyer', 'Flyer'),
        ('label', 'Label'),
        ('business_card', 'Business Card'),
        ('brochure', 'Brochure'),
        ('catalog', 'Catalog'),
        ('other', 'Other'),
    ]

    # Job identification
    job_number = models.CharField(max_length=20, unique=True, blank=True)
    client = models.ForeignKey(
        'accounts.Client',
        on_delete=models.PROTECT,
        related_name='jobs',
        help_text="Client for this job"
    )
    order_type = models.CharField(max_length=20, choices=ORDER_TYPES)
    order_name = models.CharField(max_length=200)

    # Job parameters
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of pieces to produce"
    )

    # Paper specifications
    paper_type = models.ForeignKey(
        PaperType,
        on_delete=models.PROTECT,
        help_text="Type and weight of paper"
    )
    end_size = models.ForeignKey(
        PaperSize,
        on_delete=models.PROTECT,
        related_name='jobs_end_size',
        help_text="Final product size"
    )
    printing_size = models.ForeignKey(
        PaperSize,
        on_delete=models.PROTECT,
        related_name='jobs_printing_size',
        help_text="Size used for printing"
    )
    selling_size = models.ForeignKey(
        PaperSize,
        on_delete=models.PROTECT,
        related_name='jobs_selling_size',
        help_text="Size paper is purchased in"
    )
    parts_of_selling_size = models.PositiveIntegerField(
        default=1,
        help_text="How many printing sheets fit in one purchased sheet"
    )

    # Production settings
    n_up = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Number of items per printing sheet"
    )
    printing_machine = models.ForeignKey(
        PrintingMachine,
        on_delete=models.PROTECT,
        help_text="Machine to be used for printing"
    )
    colors_front = models.PositiveIntegerField(
        default=4,
        validators=[MinValueValidator(0), MaxValueValidator(12)],
        help_text="Number of print colors on front"
    )
    colors_back = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(12)],
        help_text="Number of print colors on back"
    )
    special_colors = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of special/spot colors"
    )

    # Book-specific parameters
    number_of_pages = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total number of pages (for books only)"
    )
    n_up_signatures = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of book pages per printing sheet"
    )

    # Additional information
    notes = models.TextField(
        blank=True,
        help_text="Client remarks, agreements, and special requirements"
    )

    # Quantity variants for pricing
    variant_quantities = models.CharField(
        max_length=100,
        blank=True,
        help_text="Comma-separated additional quantities for pricing (e.g., '2000,5000')"
    )

    # Calculated totals (populated after calculation)
    total_material_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    total_labor_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    total_outsourcing_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    total_time_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total time in minutes"
    )

    # Paper calculations
    print_run = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of sheets to print (quantity / n_up)"
    )
    waste_sheets = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Additional sheets for waste"
    )
    sheets_to_buy = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total sheets to purchase"
    )
    paper_weight_kg = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Total weight of paper in kg"
    )

    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_template = models.BooleanField(
        default=False,
        help_text="Use this job as a template"
    )
    template_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Name for template (if is_template=True)"
    )

    # User tracking
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    calculated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_template']),
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['order_type']),
        ]

    def __str__(self):
        if self.is_template:
            return f"Template: {self.template_name or self.order_name}"
        return f"{self.job_number} - {self.client.company_name} ({self.order_name})"

    def get_absolute_url(self):
        return reverse('jobs:detail', kwargs={'pk': self.pk})

    @property
    def total_cost(self):
        """Calculate total cost from all components."""
        if all([self.total_material_cost, self.total_labor_cost, self.total_outsourcing_cost]):
            return self.total_material_cost + self.total_labor_cost + self.total_outsourcing_cost
        return None

    @property
    def total_colors(self):
        """Total number of colors (front + back + special)."""
        return self.colors_front + self.colors_back + self.special_colors

    @property
    def total_time(self):
        """Return total time as timedelta."""
        if self.total_time_minutes:
            return timedelta(minutes=self.total_time_minutes)
        return None

    def get_variant_quantities_list(self):
        """Parse variant quantities string into list of integers."""
        if not self.variant_quantities:
            return []
        try:
            return [int(q.strip()) for q in self.variant_quantities.split(',') if q.strip()]
        except ValueError:
            return []

    def save(self, *args, **kwargs):
        # Generate job number if not set
        if not self.job_number and not self.is_template:
            self.job_number = self._generate_job_number()
        super().save(*args, **kwargs)

    def _generate_job_number(self):
        """Generate unique job number."""
        from django.utils import timezone
        year = timezone.now().year
        # Get the count of jobs created this year
        count = Job.objects.filter(
            created_at__year=year,
            is_template=False
        ).count() + 1
        return f"JOB-{year}-{count:04d}"


class JobOperation(models.Model):
    """
    Operations included in a specific job with calculated results.
    """
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='job_operations'
    )
    operation = models.ForeignKey(
        Operation,
        on_delete=models.CASCADE,
        help_text="Reference to master operation"
    )
    sequence_order = models.PositiveIntegerField(
        help_text="Order of execution in the job"
    )

    # Snapshot of operation settings at calculation time
    operation_name = models.CharField(max_length=100)
    pricing_type = models.CharField(max_length=20)
    makeready_price = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    makeready_time_minutes = models.PositiveIntegerField()
    time_per_unit_seconds = models.PositiveIntegerField()

    # Quantities for this operation step
    quantity_before = models.PositiveIntegerField(
        help_text="Quantity entering this operation"
    )
    quantity_after = models.PositiveIntegerField(
        help_text="Quantity after this operation"
    )

    # Calculated results for this operation
    material_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    labor_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    outsourcing_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    total_time_minutes = models.PositiveIntegerField()

    # Additional operation-specific data
    colors_used = models.PositiveIntegerField(default=0)
    plates_needed = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sequence_order']
        unique_together = ['job', 'sequence_order']

    def __str__(self):
        return f"{self.job} - {self.sequence_order}. {self.operation_name}"

    @property
    def total_cost(self):
        """Total cost for this operation."""
        return self.material_cost + self.labor_cost + self.outsourcing_cost

    @property
    def total_time(self):
        """Return total time as timedelta."""
        return timedelta(minutes=self.total_time_minutes)


class JobVariant(models.Model):
    """
    Calculated costs for different quantities of the same job.
    """
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='variants'
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Quantity for this variant"
    )

    # Calculated totals for this quantity
    total_material_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    total_labor_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    total_outsourcing_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    total_time_minutes = models.PositiveIntegerField()

    # Paper calculations for this quantity
    print_run = models.PositiveIntegerField()
    waste_sheets = models.PositiveIntegerField()
    sheets_to_buy = models.PositiveIntegerField()
    paper_weight_kg = models.DecimalField(max_digits=10, decimal_places=3)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['quantity']
        unique_together = ['job', 'quantity']

    def __str__(self):
        return f"{self.job} - {self.quantity} pcs"

    @property
    def total_cost(self):
        """Total cost for this variant."""
        return self.total_material_cost + self.total_labor_cost + self.total_outsourcing_cost

    @property
    def cost_per_piece(self):
        """Cost per piece for this variant."""
        if self.quantity > 0:
            return self.total_cost / self.quantity
        return Decimal('0')

    @property
    def total_time(self):
        """Return total time as timedelta."""
        return timedelta(minutes=self.total_time_minutes)