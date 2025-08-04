"""
Models for jobs, estimates, and calculations.
"""

from datetime import timedelta
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from django.urls import reverse
from PrintEstimation.operations.models import Operation, PaperType, PaperSize

User = get_user_model()


class Job(models.Model):
    """
    Main model representing both estimates and templates.
    Contains all parameters needed for printing estimation.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('waiting_manager', 'Waiting Manager Approval / Review'),
        ('waiting_client', 'Waiting for Client Approval'), 
        ('approved', 'Approved Orders'),
        ('urgent', 'Urgent Orders'),
        ('finished', 'Finished Order'),
        ('rejected', 'Rejected'),
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
        help_text="Final product size",
        null=True,
        blank=True
    )
    # Custom end size dimensions (for non-standard sizes)
    custom_end_width = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Custom end size width in cm"
    )
    custom_end_height = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Custom end size height in cm"
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
        help_text="Parent sheet size that paper is purchased in"
    )
    parts_of_selling_size = models.PositiveIntegerField(
        default=1,
        help_text="How many printing sheets fit in one parent sheet"
    )

    # Production settings
    n_up = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Number of items per printing sheet"
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

    # Job scheduling
    deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Job completion deadline"
    )

    # Quantity variants for pricing

    # Calculated totals (populated after calculation)
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Total job cost (sum of all costs)"
    )
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
        help_text="Total parent sheets to purchase"
    )
    paper_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total cost of paper"
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
    def total_colors(self):
        """Total number of colors (front + back + special)."""
        return self.colors_front + self.colors_back + self.special_colors

    @property
    def effective_end_size_name(self):
        """Get the effective end size name (custom or standard)."""
        if self.custom_end_width and self.custom_end_height:
            return f"{self.custom_end_width}×{self.custom_end_height} cm (Custom)"
        elif self.end_size:
            return self.end_size.name
        return "Not specified"

    @property
    def effective_end_size_area_cm2(self):
        """Get the effective end size area in cm²."""
        if self.custom_end_width and self.custom_end_height:
            return float(self.custom_end_width * self.custom_end_height)
        elif self.end_size:
            return self.end_size.area_cm2
        return 0

    @property
    def total_time(self):
        """Return total time as timedelta."""
        if self.total_time_minutes:
            return timedelta(minutes=self.total_time_minutes)
        return None


    def save(self, *args, **kwargs):
        # Generate job number if not set
        if not self.job_number and not self.is_template:
            max_retries = 3
            for retry in range(max_retries):
                try:
                    self.job_number = self._generate_job_number()
                    super().save(*args, **kwargs)
                    break
                except Exception as e:
                    if retry == max_retries - 1:
                        # On final retry, use UUID fallback
                        import uuid
                        from django.utils import timezone
                        year = timezone.now().year
                        unique_id = str(uuid.uuid4())[:8].upper()
                        self.job_number = f"JOB-{year}-{unique_id}"
                        super().save(*args, **kwargs)
                        break
                    # Wait a tiny bit before retry
                    import time
                    time.sleep(0.01)
        else:
            super().save(*args, **kwargs)

    def _generate_job_number(self):
        """Generate unique job number."""
        from django.utils import timezone
        from django.db import transaction
        import re
        
        year = timezone.now().year
        
        # Get the highest existing job number for this year
        existing_jobs = Job.objects.filter(
            job_number__startswith=f"JOB-{year}-",
            is_template=False
        ).values_list('job_number', flat=True)
        
        if existing_jobs:
            # Extract numbers from existing job numbers and find the maximum
            numbers = []
            for job_num in existing_jobs:
                match = re.search(r'JOB-\d{4}-(\d{4})', job_num)
                if match:
                    numbers.append(int(match.group(1)))
            
            if numbers:
                next_number = max(numbers) + 1
            else:
                next_number = 1
        else:
            next_number = 1
        
        # Try to create unique job number with retry mechanism
        max_attempts = 100
        for attempt in range(max_attempts):
            job_number = f"JOB-{year}-{next_number + attempt:04d}"
            
            # Check if this number already exists
            if not Job.objects.filter(job_number=job_number).exists():
                return job_number
        
        # Fallback: use timestamp if all attempts failed
        import time
        timestamp = int(time.time() * 1000) % 10000
        return f"JOB-{year}-{timestamp:04d}"


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
    operation_name = models.CharField(max_length=150)
    makeready_price = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_sheet = models.DecimalField(max_digits=10, decimal_places=4)
    plate_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    makeready_time_minutes = models.PositiveIntegerField()
    cleaning_time_minutes = models.PositiveIntegerField(default=0)
    sheets_per_minute = models.PositiveIntegerField(default=1)

    # Dynamic operation parameters (e.g., cut pieces, fold count)
    operation_parameters = models.JSONField(
        blank=True, 
        null=True,
        help_text="Dynamic parameters for this operation (e.g., {'cut_pieces': 4, 'fold_count': 2})"
    )

    # Quantities for this operation step
    quantity_before = models.PositiveIntegerField(
        help_text="Quantity entering this operation"
    )
    quantity_after = models.PositiveIntegerField(
        help_text="Quantity after this operation"
    )
    waste_sheets = models.PositiveIntegerField(
        default=0,
        help_text="Waste sheets generated by this operation"
    )
    processing_quantity = models.PositiveIntegerField(
        help_text="Quantity processed (including waste)"
    )

    # Calculated results for this operation
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    total_time_minutes = models.PositiveIntegerField()

    # Additional operation-specific data
    colors_used = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sequence_order']
        unique_together = ['job', 'sequence_order']

    def __str__(self):
        return f"{self.job} - {self.sequence_order}. {self.operation_name}"

    @property
    def total_time(self):
        """Return total time as timedelta."""
        return timedelta(minutes=self.total_time_minutes)


class JobPDFExport(models.Model):
    """Track PDF exports of jobs."""
    EXPORT_TYPES = [
        ('estimate', 'Estimate/Quote'),
        ('job_sheet', 'Job Sheet'),
    ]
    
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='pdf_exports'
    )
    export_type = models.CharField(max_length=20, choices=EXPORT_TYPES)
    file_name = models.CharField(max_length=255)
    file_path = models.FileField(upload_to='exports/pdfs/')
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    file_size = models.PositiveIntegerField(default=0)  # in bytes
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Job PDF Export'
        verbose_name_plural = 'Job PDF Exports'
    
    def __str__(self):
        return f"{self.job.order_name} - {self.get_export_type_display()}"
    
    @property
    def file_size_mb(self):
        """Return file size in MB."""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0


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
    total_cost = models.DecimalField(
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
    def cost_per_piece(self):
        """Cost per piece for this variant."""
        if self.quantity > 0:
            return self.total_cost / self.quantity
        return Decimal('0')

    @property
    def total_time(self):
        """Return total time as timedelta."""
        return timedelta(minutes=self.total_time_minutes)