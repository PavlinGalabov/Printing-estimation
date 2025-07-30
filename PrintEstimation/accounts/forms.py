"""
Forms for accounts app - user and client management.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Client


class CustomUserCreationForm(UserCreationForm):
    """Custom user creation form for the custom User model."""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to password fields
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


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
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter company name'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Primary contact person'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'company@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1 (555) 123-4567'
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1 (555) 123-4567'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://company.com'
            }),
            'address_line_1': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Street address'
            }),
            'address_line_2': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apartment, suite, etc. (optional)'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'state_province': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State/Province'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Postal/ZIP code'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Country'
            }),
            'tax_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tax ID number'
            }),
            'payment_terms': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '30',
                'min': '0'
            }),
            'credit_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'discount_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes about this client'
            }),
            'special_requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Special requirements or preferences'
            }),
            'is_vip': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def clean_email(self):
        """Validate email uniqueness."""
        email = self.cleaned_data.get('email')
        if email:
            qs = Client.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("A client with this email already exists.")
        return email

    def clean_credit_limit(self):
        """Ensure credit limit is not negative."""
        credit_limit = self.cleaned_data.get('credit_limit')
        if credit_limit and credit_limit < 0:
            raise forms.ValidationError("Credit limit cannot be negative.")
        return credit_limit

    def clean_discount_percentage(self):
        """Ensure discount percentage is valid."""
        discount = self.cleaned_data.get('discount_percentage')
        if discount and (discount < 0 or discount > 100):
            raise forms.ValidationError("Discount percentage must be between 0 and 100.")
        return discount