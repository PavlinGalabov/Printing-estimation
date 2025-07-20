"""
User models for the printing estimation system.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


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
    company_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Company or organization name"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Contact phone number"
    )
    address = models.TextField(
        blank=True,
        help_text="Full address"
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about this user"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['company_name', 'last_name', 'first_name']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        if self.company_name:
            return f"{self.company_name} ({self.get_full_name() or self.username})"
        return self.get_full_name() or self.username

    def get_display_name(self):
        """Return the best display name for this user."""
        if self.get_full_name():
            return self.get_full_name()
        return self.username

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