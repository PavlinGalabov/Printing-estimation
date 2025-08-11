"""
Tests for accounts models and functionality.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from decimal import Decimal
from .models import Client

User = get_user_model()


class UserModelTest(TestCase):
    """Tests for the custom User model."""

    def setUp(self):
        """Set up test data."""
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '+1-555-123-4567',
            'notes': 'Test user notes'
        }

    def test_user_creation_with_default_type(self):
        """Test creating a user with default client type."""
        user = User.objects.create_user(**self.user_data)
        
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.user_type, 'client')
        self.assertEqual(user.phone, '+1-555-123-4567')
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)

    def test_user_display_name_methods(self):
        """Test user display name methods."""
        # Test with full name
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(str(user), 'John Doe')
        self.assertEqual(user.get_display_name(), 'John Doe')
        
        # Test with username only
        user_no_name = User.objects.create_user(
            username='usernameonly',
            email='user@example.com'
        )
        self.assertEqual(str(user_no_name), 'usernameonly')
        self.assertEqual(user_no_name.get_display_name(), 'usernameonly')

    def test_user_type_properties(self):
        """Test user type property methods."""
        # Test superuser type
        superuser = User.objects.create_user(
            username='super',
            email='super@example.com',
            user_type='superuser'
        )
        self.assertTrue(superuser.is_superuser_type)
        self.assertFalse(superuser.is_staff_type)
        self.assertFalse(superuser.is_client_type)
        
        # Test staff type
        staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            user_type='staff'
        )
        self.assertFalse(staff_user.is_superuser_type)
        self.assertTrue(staff_user.is_staff_type)
        self.assertFalse(staff_user.is_client_type)
        
        # Test client type
        client = User.objects.create_user(
            username='client',
            email='client@example.com',
            user_type='client'
        )
        self.assertFalse(client.is_superuser_type)
        self.assertFalse(client.is_staff_type)
        self.assertTrue(client.is_client_type)

    def test_is_staff_user_method(self):
        """Test the is_staff_user method with different scenarios."""
        # Test staff user type
        staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            user_type='staff'
        )
        self.assertTrue(staff_user.is_staff_user())
        
        # Test Django is_staff flag
        django_staff = User.objects.create_user(
            username='djangostaff',
            email='djangostaff@example.com',
            is_staff=True
        )
        self.assertTrue(django_staff.is_staff_user())
        
        # Test Django superuser
        superuser = User.objects.create_superuser(
            username='super',
            email='super@example.com',
            password='testpass123'
        )
        self.assertTrue(superuser.is_staff_user())
        
        # Test regular client
        client = User.objects.create_user(
            username='client',
            email='client@example.com'
        )
        self.assertFalse(client.is_staff_user())

    def test_user_meta_ordering(self):
        """Test that users are ordered correctly."""
        User.objects.create_user(username='charlie', last_name='Charlie', first_name='C')
        User.objects.create_user(username='alpha', last_name='Alpha', first_name='A')  
        User.objects.create_user(username='beta', last_name='Beta', first_name='B')
        
        users = list(User.objects.all())
        self.assertEqual(users[0].last_name, 'Alpha')
        self.assertEqual(users[1].last_name, 'Beta')
        self.assertEqual(users[2].last_name, 'Charlie')


class ClientModelTest(TestCase):
    """Tests for the Client model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='clientuser',
            email='client@example.com'
        )
        
        self.client_data = {
            'company_name': 'Test Company Inc.',
            'contact_person': 'Jane Smith',
            'email': 'contact@testcompany.com',
            'phone': '+1-555-987-6543',
            'mobile': '+1-555-111-2222',
            'website': 'https://testcompany.com',
            'address_line_1': '123 Business St',
            'address_line_2': 'Suite 100',
            'city': 'Business City',
            'state_province': 'BC',
            'postal_code': '12345',
            'country': 'Canada',
            'tax_number': 'TAX123456',
            'payment_terms': 'net_30',
            'credit_limit': Decimal('5000.00'),
            'discount_percentage': Decimal('5.00'),
            'notes': 'Important client',
            'special_requirements': 'High quality paper only',
            'is_vip': True,
            'user': self.user
        }

    def test_client_creation(self):
        """Test creating a client with all fields."""
        client = Client.objects.create(**self.client_data)
        
        self.assertEqual(client.company_name, 'Test Company Inc.')
        self.assertEqual(client.email, 'contact@testcompany.com')
        self.assertEqual(client.payment_terms, 'net_30')
        self.assertEqual(client.credit_limit, Decimal('5000.00'))
        self.assertEqual(client.discount_percentage, Decimal('5.00'))
        self.assertTrue(client.is_active)
        self.assertTrue(client.is_vip)
        self.assertEqual(client.user, self.user)

    def test_client_string_representation(self):
        """Test client string representation."""
        client = Client.objects.create(**self.client_data)
        self.assertEqual(str(client), 'Test Company Inc.')

    def test_client_full_address_property(self):
        """Test the full_address property."""
        client = Client.objects.create(**self.client_data)
        expected_address = (
            "123 Business St\n"
            "Suite 100\n"
            "Business City, BC 12345\n"
            "Canada"
        )
        self.assertEqual(client.full_address, expected_address)
        
        # Test with minimal address
        minimal_client = Client.objects.create(
            company_name='Minimal Co',
            email='minimal@example.com',
            city='City',
            country='Country'
        )
        expected_minimal = "City,\nCountry"
        self.assertEqual(minimal_client.full_address, expected_minimal)

    def test_client_primary_contact_property(self):
        """Test the primary_contact property."""
        client = Client.objects.create(**self.client_data)
        expected_contact = 'Jane Smith (contact@testcompany.com)'
        self.assertEqual(client.primary_contact, expected_contact)
        
        # Test without contact person
        no_contact_client = Client.objects.create(
            company_name='No Contact Co',
            email='nocontact@example.com'
        )
        self.assertEqual(no_contact_client.primary_contact, 'nocontact@example.com')

    def test_client_validation_constraints(self):
        """Test client model validation and constraints."""
        # Test email uniqueness would be handled by form validation
        client1 = Client.objects.create(
            company_name='Company 1',
            email='duplicate@example.com'
        )
        
        # This should work as model doesn't enforce email uniqueness
        client2 = Client.objects.create(
            company_name='Company 2', 
            email='duplicate@example.com'
        )
        
        self.assertNotEqual(client1.pk, client2.pk)
        
    def test_client_get_jobs_count_safe_method(self):
        """Test get_jobs_count method handles missing relationships gracefully."""
        client = Client.objects.create(**self.client_data)
        # Should not raise exception even if jobs relationship doesn't exist yet
        jobs_count = client.get_jobs_count()
        self.assertEqual(jobs_count, 0)

    def test_client_get_total_revenue_safe_method(self):
        """Test get_total_revenue method handles missing relationships gracefully."""
        client = Client.objects.create(**self.client_data)
        # Should not raise exception even if jobs relationship doesn't exist yet
        total_revenue = client.get_total_revenue()
        self.assertEqual(total_revenue, 0)

    def test_client_meta_ordering(self):
        """Test that clients are ordered by company name."""
        Client.objects.create(company_name='Zebra Corp', email='zebra@example.com')
        Client.objects.create(company_name='Alpha Inc', email='alpha@example.com')
        Client.objects.create(company_name='Beta LLC', email='beta@example.com')
        
        clients = list(Client.objects.all())
        self.assertEqual(clients[0].company_name, 'Alpha Inc')
        self.assertEqual(clients[1].company_name, 'Beta LLC')
        self.assertEqual(clients[2].company_name, 'Zebra Corp')
