"""
User and Client models for the printing estimation system.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class User(AbstractUser):
    """
    Custom User model with additional fields for printing business.
    """
    USER_TYPES = [
        ('superuser', 'Superuser'),
        ('staff', 'Staff'),
        ('client', 'Client'),
    ]

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPES,
        default='client',
        help_text="User role in the system"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Contact phone number"
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about this user"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name', 'username']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.get_full_name() or self.username

    def get_display_name(self):
        """Return the best display name for this user."""
        if self.get_full_name():
            return self.get_full_name()
        return self.username

    def is_staff_user(self):
        """Check if user has staff-level permissions."""
        return (self.user_type == 'staff' or 
                self.is_staff or 
                self.is_superuser)

    @property
    def is_superuser_type(self):
        """Check if user is superuser type."""
        return self.user_type == 'superuser'

    @property
    def is_staff_type(self):
        """Check if user is staff type."""
        return self.user_type == 'staff'

    @property
    def is_client_type(self):
        """Check if user is client type."""
        return self.user_type == 'client'


class Client(models.Model):
    """
    Client/Customer model for managing client information.
    """
    PAYMENT_TERMS = [
        ('immediate', 'Immediate'),
        ('net_7', 'Net 7 days'),
        ('net_15', 'Net 15 days'),
        ('net_30', 'Net 30 days'),
        ('net_60', 'Net 60 days'),
        ('custom', 'Custom'),
    ]

    # Basic Information
    company_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)

    # Address Information
    address_line_1 = models.CharField(max_length=200, blank=True)
    address_line_2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state_province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='Bulgaria')

    # Business Information
    tax_number = models.CharField(max_length=50, blank=True, help_text="VAT/Tax ID")
    payment_terms = models.CharField(max_length=20, choices=PAYMENT_TERMS, default='net_30')
    credit_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum credit allowed"
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Default discount percentage for this client"
    )

    # Internal Notes
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about this client"
    )
    special_requirements = models.TextField(
        blank=True,
        help_text="Special printing requirements or preferences"
    )

    # Status
    is_active = models.BooleanField(default=True)
    is_vip = models.BooleanField(default=False, help_text="VIP client with special treatment")

    # Associated user account (optional)
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Associated user account for client portal access"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['company_name']
        indexes = [
            models.Index(fields=['company_name']),
            models.Index(fields=['email']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.company_name

    def get_absolute_url(self):
        return reverse('accounts:client_detail', kwargs={'pk': self.pk})

    @property
    def full_address(self):
        """Return formatted full address."""
        address_parts = [
            self.address_line_1,
            self.address_line_2,
            f"{self.city}, {self.state_province} {self.postal_code}".strip(),
            self.country
        ]
        return '\n'.join([part for part in address_parts if part])

    @property
    def primary_contact(self):
        """Return primary contact information."""
        if self.contact_person:
            return f"{self.contact_person} ({self.email})"
        return self.email

    def get_jobs_count(self):
        """Get total number of jobs for this client."""
        try:
            return self.jobs.count()
        except Exception:
            # If there's any import error, return 0
            return 0

    def get_total_revenue(self):
        """Calculate total revenue from this client."""
        try:
            from django.db.models import Sum
            from django.apps import apps
            
            # Use apps.get_model to avoid import issues
            Job = apps.get_model('jobs', 'Job')
            
            total = Job.objects.filter(
                client=self,
                status__in=['approved', 'completed']
            ).aggregate(
                total=Sum('total_material_cost') + Sum('total_labor_cost') + Sum('total_outsourcing_cost')
            )['total']

            return total or 0
        except Exception:
            # If there's any import error, return 0
            return 0