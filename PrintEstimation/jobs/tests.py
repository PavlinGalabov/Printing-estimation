"""
Tests for job models and functionality.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import Job, JobOperation, JobVariant
from PrintEstimation.accounts.models import Client
from PrintEstimation.operations.models import Operation, PaperType, PaperSize, OperationCategory

User = get_user_model()


class JobModelTest(TestCase):
    """Tests for the Job model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        
        self.client = Client.objects.create(
            company_name='Test Client',
            email='client@example.com'
        )
        
        self.paper_type = PaperType.objects.create(
            name='Standard Paper',
            weight_gsm=80,
            price_per_kg=Decimal('2.50')
        )
        
        self.paper_size_a4 = PaperSize.objects.create(
            name='A4',
            width_cm=Decimal('21.0'),
            height_cm=Decimal('29.7'),
            is_standard=True
        )
        
        self.paper_size_a3 = PaperSize.objects.create(
            name='A3',
            width_cm=Decimal('29.7'),
            height_cm=Decimal('42.0'),
            is_standard=True
        )
        
        self.job_data = {
            'client': self.client,
            'order_type': 'flyer',
            'order_name': 'Test Flyer Campaign',
            'quantity': 1000,
            'paper_type': self.paper_type,
            'end_size': self.paper_size_a4,
            'printing_size': self.paper_size_a3,
            'selling_size': self.paper_size_a3,
            'parts_of_selling_size': 2,
            'n_up': 2,
            'colors_front': 4,
            'colors_back': 1,
            'special_colors': 0,
            'created_by': self.user
        }

    def test_job_creation_and_job_number_generation(self):
        """Test creating a job with automatic job number generation."""
        job = Job.objects.create(**self.job_data)
        
        self.assertEqual(job.client, self.client)
        self.assertEqual(job.order_name, 'Test Flyer Campaign')
        self.assertEqual(job.quantity, 1000)
        self.assertEqual(job.status, 'draft')
        self.assertIsNotNone(job.job_number)
        self.assertTrue(job.job_number.startswith('JOB-'))
        self.assertFalse(job.is_template)

    def test_job_string_representation(self):
        """Test job string representation."""
        job = Job.objects.create(**self.job_data)
        expected_str = f"{job.job_number} - {self.client.company_name} (Test Flyer Campaign)"
        self.assertEqual(str(job), expected_str)
        
        # Test template string representation
        template_job = Job.objects.create(
            **{**self.job_data, 'is_template': True, 'template_name': 'Flyer Template'}
        )
        self.assertEqual(str(template_job), "Template: Flyer Template")

    def test_job_total_colors_property(self):
        """Test total_colors property calculation."""
        job = Job.objects.create(**self.job_data)
        expected_total = 4 + 1 + 0  # front + back + special
        self.assertEqual(job.total_colors, expected_total)

    def test_job_effective_end_size_properties(self):
        """Test effective end size properties with standard and custom sizes."""
        # Test with standard size
        job = Job.objects.create(**self.job_data)
        self.assertEqual(job.effective_end_size_name, 'A4')
        self.assertAlmostEqual(job.effective_end_size_area_cm2, float(21.0 * 29.7), places=1)
        
        # Test with custom size
        custom_job_data = {**self.job_data}
        custom_job_data['end_size'] = None
        custom_job_data['custom_end_width'] = Decimal('15.0')
        custom_job_data['custom_end_height'] = Decimal('20.0')
        
        custom_job = Job.objects.create(**custom_job_data)
        self.assertEqual(custom_job.effective_end_size_name, "15.0×20.0 cm (Custom)")
        self.assertEqual(custom_job.effective_end_size_area_cm2, 300.0)

    def test_job_operations_cost_property(self):
        """Test operations_cost property calculation."""
        job = Job.objects.create(**self.job_data)
        job.total_material_cost = Decimal('100.00')
        job.paper_cost = Decimal('30.00')
        job.save()
        
        self.assertEqual(job.operations_cost, Decimal('70.00'))
        
        # Test with None values
        job.total_material_cost = None
        job.paper_cost = None
        job.save()
        job.refresh_from_db()
        self.assertEqual(job.operations_cost, Decimal('0'))

    def test_job_total_time_property(self):
        """Test total_time property returns timedelta."""
        job = Job.objects.create(**self.job_data)
        job.total_time_minutes = 120
        job.save()
        
        self.assertEqual(job.total_time, timedelta(minutes=120))
        
        job.total_time_minutes = None
        job.save()
        job.refresh_from_db()
        self.assertIsNone(job.total_time)

    def test_job_unique_job_number_generation(self):
        """Test that job numbers are unique."""
        job1 = Job.objects.create(**self.job_data)
        job2 = Job.objects.create(**{**self.job_data, 'order_name': 'Second Job'})
        
        self.assertNotEqual(job1.job_number, job2.job_number)
        self.assertTrue(job1.job_number.startswith('JOB-'))
        self.assertTrue(job2.job_number.startswith('JOB-'))

    def test_template_job_no_job_number(self):
        """Test that template jobs don't get job numbers."""
        template_data = {**self.job_data, 'is_template': True, 'template_name': 'Test Template'}
        template_job = Job.objects.create(**template_data)
        
        self.assertTrue(template_job.is_template)
        self.assertEqual(template_job.template_name, 'Test Template')
        self.assertEqual(template_job.job_number, '')


class JobOperationModelTest(TestCase):
    """Tests for the JobOperation model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.client = Client.objects.create(company_name='Test Client', email='client@example.com')
        
        self.paper_type = PaperType.objects.create(name='Paper', weight_gsm=80, price_per_kg=Decimal('2.50'))
        self.paper_size = PaperSize.objects.create(name='A4', width_cm=Decimal('21.0'), height_cm=Decimal('29.7'))
        
        self.job = Job.objects.create(
            client=self.client,
            order_type='flyer',
            order_name='Test Job',
            quantity=1000,
            paper_type=self.paper_type,
            printing_size=self.paper_size,
            selling_size=self.paper_size,
            created_by=self.user
        )
        
        self.operation_category = OperationCategory.objects.create(
            name='Printing',
            description='Printing operations'
        )
        
        self.operation = Operation.objects.create(
            name='Color Printing',
            category=self.operation_category,
            makeready_price=Decimal('15.00'),
            price_per_sheet=Decimal('0.05'),
            makeready_time_minutes=30,
            sheets_per_minute=100
        )

    def test_job_operation_creation(self):
        """Test creating a job operation."""
        job_operation = JobOperation.objects.create(
            job=self.job,
            operation=self.operation,
            sequence_order=1,
            operation_name='Color Printing',
            makeready_price=Decimal('15.00'),
            price_per_sheet=Decimal('0.05'),
            makeready_time_minutes=30,
            sheets_per_minute=100,
            quantity_before=1000,
            quantity_after=1000,
            processing_quantity=1030,
            total_cost=Decimal('66.50'),
            total_time_minutes=40
        )
        
        self.assertEqual(job_operation.job, self.job)
        self.assertEqual(job_operation.operation, self.operation)
        self.assertEqual(job_operation.sequence_order, 1)
        self.assertEqual(job_operation.total_cost, Decimal('66.50'))

    def test_job_operation_string_representation(self):
        """Test JobOperation string representation."""
        job_operation = JobOperation.objects.create(
            job=self.job,
            operation=self.operation,
            sequence_order=1,
            operation_name='Color Printing',
            makeready_price=Decimal('15.00'),
            price_per_sheet=Decimal('0.05'),
            makeready_time_minutes=30,
            quantity_before=1000,
            quantity_after=1000,
            processing_quantity=1000,
            total_cost=Decimal('50.00'),
            total_time_minutes=30
        )
        
        expected_str = f"{self.job} - 1. Color Printing"
        self.assertEqual(str(job_operation), expected_str)

    def test_job_operation_total_time_property(self):
        """Test total_time property returns timedelta."""
        job_operation = JobOperation.objects.create(
            job=self.job,
            operation=self.operation,
            sequence_order=1,
            operation_name='Color Printing',
            makeready_price=Decimal('15.00'),
            price_per_sheet=Decimal('0.05'),
            makeready_time_minutes=30,
            quantity_before=1000,
            quantity_after=1000,
            processing_quantity=1000,
            total_cost=Decimal('50.00'),
            total_time_minutes=45
        )
        
        self.assertEqual(job_operation.total_time, timedelta(minutes=45))

    def test_job_operation_sequencing_and_calculations(self):
        """Test job operation sequencing and quantity calculations."""
        # First operation - printing
        printing_op = JobOperation.objects.create(
            job=self.job,
            operation=self.operation,
            sequence_order=1,
            operation_name='Printing',
            makeready_price=Decimal('15.00'),
            price_per_sheet=Decimal('0.05'),
            makeready_time_minutes=30,
            quantity_before=500,  # print run (quantity/n_up)
            quantity_after=500,
            waste_sheets=30,
            processing_quantity=530,  # includes waste
            total_cost=Decimal('41.50'),  # 15.00 + (530 * 0.05)
            total_time_minutes=35
        )
        
        # Second operation - cutting (multiplies quantity)
        cutting_category = OperationCategory.objects.create(name='Cutting')
        cutting_operation = Operation.objects.create(
            name='Cutting',
            category=cutting_category,
            makeready_price=Decimal('5.00'),
            price_per_sheet=Decimal('0.02')
        )
        
        cutting_op = JobOperation.objects.create(
            job=self.job,
            operation=cutting_operation,
            sequence_order=2,
            operation_name='Cutting',
            makeready_price=Decimal('5.00'),
            price_per_sheet=Decimal('0.02'),
            makeready_time_minutes=15,
            quantity_before=500,
            quantity_after=1000,  # doubled due to cutting
            processing_quantity=500,
            total_cost=Decimal('15.00'),  # 5.00 + (500 * 0.02)
            total_time_minutes=20
        )
        
        operations = self.job.job_operations.all().order_by('sequence_order')
        self.assertEqual(operations[0], printing_op)
        self.assertEqual(operations[1], cutting_op)
        self.assertEqual(operations[0].quantity_after, 500)
        self.assertEqual(operations[1].quantity_after, 1000)

    def test_job_operation_parameters_json_field(self):
        """Test operation_parameters JSON field functionality."""
        job_operation = JobOperation.objects.create(
            job=self.job,
            operation=self.operation,
            sequence_order=1,
            operation_name='Custom Cutting',
            makeready_price=Decimal('5.00'),
            price_per_sheet=Decimal('0.02'),
            makeready_time_minutes=15,
            operation_parameters={'cut_pieces': 4, 'cut_type': 'straight'},
            quantity_before=1000,
            quantity_after=4000,
            processing_quantity=1000,
            total_cost=Decimal('25.00'),
            total_time_minutes=25
        )
        
        job_operation.refresh_from_db()
        self.assertEqual(job_operation.operation_parameters['cut_pieces'], 4)
        self.assertEqual(job_operation.operation_parameters['cut_type'], 'straight')


class JobVariantModelTest(TestCase):
    """Tests for the JobVariant model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.client = Client.objects.create(company_name='Test Client', email='client@example.com')
        
        self.paper_type = PaperType.objects.create(name='Paper', weight_gsm=80, price_per_kg=Decimal('2.50'))
        self.paper_size = PaperSize.objects.create(name='A4', width_cm=Decimal('21.0'), height_cm=Decimal('29.7'))
        
        self.job = Job.objects.create(
            client=self.client,
            order_type='flyer',
            order_name='Test Job',
            quantity=1000,
            paper_type=self.paper_type,
            printing_size=self.paper_size,
            selling_size=self.paper_size,
            created_by=self.user
        )

    def test_job_variant_creation(self):
        """Test creating a job variant with cost calculations."""
        variant = JobVariant.objects.create(
            job=self.job,
            quantity=500,
            total_cost=Decimal('120.50'),
            total_time_minutes=45,
            print_run=250,
            waste_sheets=30,
            sheets_to_buy=280,
            paper_weight_kg=Decimal('5.6'),
            paper_cost=Decimal('14.00'),
            operations_cost=Decimal('106.50')
        )
        
        self.assertEqual(variant.job, self.job)
        self.assertEqual(variant.quantity, 500)
        self.assertEqual(variant.total_cost, Decimal('120.50'))
        self.assertEqual(variant.paper_cost, Decimal('14.00'))
        self.assertEqual(variant.operations_cost, Decimal('106.50'))

    def test_job_variant_string_representation(self):
        """Test JobVariant string representation."""
        variant = JobVariant.objects.create(
            job=self.job,
            quantity=1000,
            total_cost=Decimal('200.00'),
            total_time_minutes=60,
            print_run=500,
            waste_sheets=50,
            sheets_to_buy=550,
            paper_weight_kg=Decimal('11.0')
        )
        
        expected_str = f"{self.job} - 1000 pcs"
        self.assertEqual(str(variant), expected_str)

    def test_job_variant_cost_per_piece_property(self):
        """Test cost_per_piece property calculation."""
        variant = JobVariant.objects.create(
            job=self.job,
            quantity=1000,
            total_cost=Decimal('150.00'),
            total_time_minutes=60,
            print_run=500,
            waste_sheets=50,
            sheets_to_buy=550,
            paper_weight_kg=Decimal('11.0')
        )
        
        self.assertEqual(variant.cost_per_piece, Decimal('0.15'))
        
        # Test with zero quantity
        zero_variant = JobVariant.objects.create(
            job=self.job,
            quantity=0,
            total_cost=Decimal('100.00'),
            total_time_minutes=30,
            print_run=0,
            waste_sheets=0,
            sheets_to_buy=0,
            paper_weight_kg=Decimal('0')
        )
        
        self.assertEqual(zero_variant.cost_per_piece, Decimal('0'))

    def test_job_variant_total_time_property(self):
        """Test total_time property returns timedelta."""
        variant = JobVariant.objects.create(
            job=self.job,
            quantity=2000,
            total_cost=Decimal('300.00'),
            total_time_minutes=90,
            print_run=1000,
            waste_sheets=100,
            sheets_to_buy=1100,
            paper_weight_kg=Decimal('22.0')
        )
        
        self.assertEqual(variant.total_time, timedelta(minutes=90))

    def test_job_variant_unique_constraint(self):
        """Test that job variants have unique quantity per job."""
        # Create first variant
        JobVariant.objects.create(
            job=self.job,
            quantity=1000,
            total_cost=Decimal('200.00'),
            total_time_minutes=60,
            print_run=500,
            waste_sheets=50,
            sheets_to_buy=550,
            paper_weight_kg=Decimal('11.0')
        )
        
        # Attempt to create duplicate quantity should raise integrity error
        with self.assertRaises(Exception):  # IntegrityError or ValidationError
            JobVariant.objects.create(
                job=self.job,
                quantity=1000,  # Same quantity
                total_cost=Decimal('180.00'),
                total_time_minutes=55,
                print_run=500,
                waste_sheets=50,
                sheets_to_buy=550,
                paper_weight_kg=Decimal('11.0')
            )

    def test_job_variant_ordering(self):
        """Test that variants are ordered by quantity."""
        # Create variants in non-sequential order
        variant_2000 = JobVariant.objects.create(
            job=self.job, quantity=2000, total_cost=Decimal('300.00'),
            total_time_minutes=90, print_run=1000, waste_sheets=100,
            sheets_to_buy=1100, paper_weight_kg=Decimal('22.0')
        )
        
        variant_500 = JobVariant.objects.create(
            job=self.job, quantity=500, total_cost=Decimal('120.00'),
            total_time_minutes=40, print_run=250, waste_sheets=30,
            sheets_to_buy=280, paper_weight_kg=Decimal('5.6')
        )
        
        variant_1000 = JobVariant.objects.create(
            job=self.job, quantity=1000, total_cost=Decimal('200.00'),
            total_time_minutes=60, print_run=500, waste_sheets=50,
            sheets_to_buy=550, paper_weight_kg=Decimal('11.0')
        )
        
        variants = list(self.job.variants.all())
        self.assertEqual(variants[0].quantity, 500)
        self.assertEqual(variants[1].quantity, 1000)
        self.assertEqual(variants[2].quantity, 2000)
