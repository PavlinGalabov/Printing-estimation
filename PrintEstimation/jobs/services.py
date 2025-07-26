"""
Calculation services for printing job estimation.
Implements the formula-based approach for cost and time calculations.
"""

from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db import models
from .models import Job, JobOperation, JobVariant
from PrintEstimation.operations.models import Operation


class PrintingCalculator:
    """
    Main calculation engine for printing jobs.
    Implements your formula-based approach with sequential operations.
    """

    def __init__(self, job):
        self.job = job
        self.current_quantity = 0
        self.total_cost = Decimal('0')
        self.total_time = 0  # in minutes
        self.operations_data = []

    def calculate_job(self):
        """
        Main calculation method that processes all operations sequentially.
        Returns complete calculation breakdown.
        """
        # Step 1: Calculate initial paper requirements
        self._calculate_paper_requirements()

        # Step 2: Get operations for this job
        job_operations = self.job.job_operations.all().order_by('sequence_order')

        if not job_operations.exists():
            return {
                'success': False,
                'error': 'No operations defined for this job. Please add operations first.'
            }

        # Step 3: Process each operation sequentially
        self.current_quantity = self.job.sheets_to_buy
        self.total_cost = Decimal('0')
        self.total_time = 0
        self.operations_data = []

        for job_operation in job_operations:
            operation_result = self._calculate_operation(job_operation.operation)

            if not operation_result['success']:
                return operation_result

            # Update job operation with calculated values
            self._update_job_operation(job_operation, operation_result)

            # Update running totals
            self.total_cost += operation_result['total_cost']
            self.total_time += operation_result['total_time_minutes']

            # Update current quantity for next operation
            self.current_quantity = operation_result['quantity_after']

            # Store operation data for breakdown
            self.operations_data.append(operation_result)

        # Step 4: Update job totals
        self._update_job_totals()

        # Step 5: Calculate quantity variants if specified
        variants_data = []
        if self.job.variant_quantities:
            variants_data = self._calculate_variants()

        return {
            'success': True,
            'job': self.job,
            'operations': self.operations_data,
            'variants': variants_data,
            'total_cost': self.total_cost,
            'total_time_minutes': self.total_time,
            'total_time_formatted': self._format_time(self.total_time)
        }

    def _calculate_paper_requirements(self):
        """Calculate paper requirements based on job parameters."""
        # Calculate print run (quantity / n_up)
        print_run = self.job.quantity // self.job.n_up
        if self.job.quantity % self.job.n_up > 0:
            print_run += 1  # Round up for partial sheets

        # Calculate waste (will be refined by operations that generate waste)
        # For now, use a basic 5% waste
        waste_sheets = int(print_run * 0.05)

        # Total sheets to buy
        sheets_to_buy = print_run + waste_sheets

        # Calculate paper weight
        paper_area_m2 = self.job.selling_size.area_m2
        paper_weight_kg = (
            Decimal(str(paper_area_m2)) *
            Decimal(str(self.job.paper_type.weight_gsm)) *
            Decimal(str(sheets_to_buy)) / 1000
        )

        # Update job with calculated values
        self.job.print_run = print_run
        self.job.waste_sheets = waste_sheets
        self.job.sheets_to_buy = sheets_to_buy
        self.job.paper_weight_kg = paper_weight_kg
        self.job.save()

    def _calculate_operation(self, operation):
        """
        Calculate cost and time for a single operation using your formulas.

        Based on your examples:
        - Color Printing: number_of_plates * (PLATE_PRICE + MAKE_READY_PRICE + print_quantity * PRICE_PER_SHEET)
        - Die-cutting: MAKE_READY_PRICE + print_quantity * PRICE_PER_SHEET
        """
        try:
            # Prepare job parameters for calculation
            job_params = {
                'quantity': self.job.quantity,
                'n_up': self.job.n_up,
                'colors_front': self.job.colors_front,
                'colors_back': self.job.colors_back,
                'print_run': self.job.print_run,
                'current_quantity': self.current_quantity,
                'paper_weight_kg': float(self.job.paper_weight_kg or 0),
            }

            # Use the operation's built-in calculation methods
            cost_result = operation.calculate_cost(job_params)
            time_minutes = operation.calculate_time(job_params)

            return {
                'success': True,
                'operation': operation,
                'quantity_before': self.current_quantity,
                'quantity_after': cost_result['quantity_after'],
                'waste_sheets': cost_result['waste_sheets'],
                'processing_quantity': cost_result['processing_quantity'],
                'total_cost': Decimal(str(cost_result['total_cost'])),
                'total_time_minutes': time_minutes,
                'colors_used': job_params['colors_front'] + job_params['colors_back'] if operation.uses_colors else 0,
                'formula_breakdown': self._get_formula_breakdown(operation, job_params, cost_result)
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error calculating operation "{operation.name}": {str(e)}'
            }

    def _get_formula_breakdown(self, operation, job_params, cost_result):
        """Generate human-readable formula breakdown."""
        breakdown = {
            'operation_type': 'Color Printing' if operation.uses_colors else 'Standard Operation',
            'makeready_price': float(operation.makeready_price),
            'price_per_sheet': float(operation.price_per_sheet),
        }

        if operation.uses_colors:
            total_colors = job_params['colors_front'] + job_params['colors_back']
            breakdown.update({
                'total_colors': total_colors,
                'plate_price': float(operation.plate_price),
                'plates_cost': total_colors * float(operation.plate_price),
                'formula': f"{total_colors} colors × (€{operation.plate_price} plate + €{operation.makeready_price} makeready + {cost_result['processing_quantity']} sheets × €{operation.price_per_sheet})"
            })
        else:
            breakdown.update({
                'formula': f"€{operation.makeready_price} makeready + {cost_result['processing_quantity']} sheets × €{operation.price_per_sheet}"
            })

        return breakdown

    def _update_job_operation(self, job_operation, operation_result):
        """Update JobOperation with calculated values."""
        operation = operation_result['operation']

        job_operation.operation_name = operation.name
        job_operation.makeready_price = operation.makeready_price
        job_operation.price_per_sheet = operation.price_per_sheet
        job_operation.plate_price = operation.plate_price
        job_operation.makeready_time_minutes = operation.makeready_time_minutes
        job_operation.cleaning_time_minutes = operation.cleaning_time_minutes
        job_operation.sheets_per_minute = operation.sheets_per_minute

        job_operation.quantity_before = operation_result['quantity_before']
        job_operation.quantity_after = operation_result['quantity_after']
        job_operation.waste_sheets = operation_result['waste_sheets']
        job_operation.processing_quantity = operation_result['processing_quantity']

        job_operation.total_cost = operation_result['total_cost']
        job_operation.total_time_minutes = operation_result['total_time_minutes']
        job_operation.colors_used = operation_result['colors_used']

        job_operation.save()

    def _update_job_totals(self):
        """Update job with calculated totals."""
        self.job.total_material_cost = self.total_cost  # For now, all costs are material
        self.job.total_labor_cost = Decimal('0')
        self.job.total_outsourcing_cost = Decimal('0')
        self.job.total_time_minutes = self.total_time
        self.job.status = 'calculated'
        self.job.calculated_at = timezone.now()
        self.job.save()

    def _calculate_variants(self):
        """Calculate costs for different quantities."""
        variants_data = []
        variant_quantities = self.job.get_variant_quantities_list()

        if not variant_quantities:
            return variants_data

        # Store original values
        original_quantity = self.job.quantity
        original_print_run = self.job.print_run
        original_waste_sheets = self.job.waste_sheets
        original_sheets_to_buy = self.job.sheets_to_buy

        # Clear existing variants
        self.job.variants.all().delete()

        # Calculate for each variant quantity
        for variant_qty in variant_quantities:
            # Temporarily update job quantity
            self.job.quantity = variant_qty
            self._calculate_paper_requirements()

            # Calculate total cost for this quantity
            variant_cost = Decimal('0')
            variant_time = 0

            job_operations = self.job.job_operations.all().order_by('sequence_order')
            current_qty = self.job.sheets_to_buy

            for job_operation in job_operations:
                job_params = {
                    'quantity': variant_qty,
                    'n_up': self.job.n_up,
                    'colors_front': self.job.colors_front,
                    'colors_back': self.job.colors_back,
                    'print_run': self.job.print_run,
                    'current_quantity': current_qty,
                    'paper_weight_kg': float(self.job.paper_weight_kg or 0),
                }

                cost_result = job_operation.operation.calculate_cost(job_params)
                time_result = job_operation.operation.calculate_time(job_params)

                variant_cost += Decimal(str(cost_result['total_cost']))
                variant_time += time_result
                current_qty = cost_result['quantity_after']

            # Create JobVariant record
            variant = JobVariant.objects.create(
                job=self.job,
                quantity=variant_qty,
                total_cost=variant_cost,
                total_time_minutes=variant_time,
                print_run=self.job.print_run,
                waste_sheets=self.job.waste_sheets,
                sheets_to_buy=self.job.sheets_to_buy,
                paper_weight_kg=self.job.paper_weight_kg
            )

            variants_data.append({
                'quantity': variant_qty,
                'total_cost': variant_cost,
                'cost_per_piece': variant.cost_per_piece,
                'total_time_minutes': variant_time,
                'total_time_formatted': self._format_time(variant_time)
            })

        # Restore original values
        self.job.quantity = original_quantity
        self.job.print_run = original_print_run
        self.job.waste_sheets = original_waste_sheets
        self.job.sheets_to_buy = original_sheets_to_buy
        self.job.save()

        return variants_data

    def _format_time(self, minutes):
        """Format time in minutes to human-readable string."""
        if minutes < 60:
            return f"{minutes} minutes"

        hours = minutes // 60
        remaining_minutes = minutes % 60

        if remaining_minutes == 0:
            return f"{hours} hour{'s' if hours != 1 else ''}"
        else:
            return f"{hours}h {remaining_minutes}m"


class JobOperationManager:
    """
    Service for managing operations within a job.
    """

    @staticmethod
    def add_operation(job, operation, sequence_order=None):
        """Add an operation to a job."""
        if sequence_order is None:
            # Add at the end
            sequence_order = job.job_operations.count() + 1

        # Shift existing operations if inserting in middle
        if sequence_order <= job.job_operations.count():
            job.job_operations.filter(
                sequence_order__gte=sequence_order
            ).update(sequence_order=models.F('sequence_order') + 1)

        job_operation = JobOperation.objects.create(
            job=job,
            operation=operation,
            sequence_order=sequence_order,
            operation_name=operation.name,
            makeready_price=operation.makeready_price,
            price_per_sheet=operation.price_per_sheet,
            plate_price=operation.plate_price,
            makeready_time_minutes=operation.makeready_time_minutes,
            cleaning_time_minutes=operation.cleaning_time_minutes,
            sheets_per_minute=operation.sheets_per_minute,
            quantity_before=0,
            quantity_after=0,
            waste_sheets=0,
            processing_quantity=0,  # Add this required field
            total_cost=Decimal('0'),
            total_time_minutes=0
        )

        return job_operation

    @staticmethod
    def remove_operation(job_operation):
        """Remove an operation from a job."""
        sequence_order = job_operation.sequence_order
        job = job_operation.job

        job_operation.delete()

        # Reorder remaining operations
        job.job_operations.filter(
            sequence_order__gt=sequence_order
        ).update(sequence_order=models.F('sequence_order') - 1)

    @staticmethod
    def reorder_operations(job, operation_ids):
        """Reorder operations based on list of operation IDs."""
        from django.db import transaction, connection
        
        with transaction.atomic():
            # Convert operation_ids to integers and validate
            try:
                operation_ids = [int(op_id) for op_id in operation_ids if str(op_id).isdigit()]
            except (ValueError, TypeError):
                raise ValueError("Invalid operation IDs provided")
            
            if not operation_ids:
                return
            
            # Get all operations for this job
            job_operations = list(JobOperation.objects.filter(job=job).order_by('id'))
            
            if len(operation_ids) != len(job_operations):
                raise ValueError("Operation count mismatch")
            
            # Validate all operation IDs exist and belong to this job
            existing_ids = {op.id for op in job_operations}
            provided_ids = set(operation_ids)
            
            if not provided_ids.issubset(existing_ids):
                raise ValueError("Some operation IDs don't belong to this job")
            
            # Method 1: Try using raw SQL to bypass constraint temporarily
            try:
                with connection.cursor() as cursor:
                    # Get table name
                    table_name = JobOperation._meta.db_table
                    
                    # Set all sequence_order to NULL temporarily (if column allows it)
                    # or to a large offset to avoid conflicts
                    max_sequence = len(job_operations) * 1000
                    
                    for i, operation_id in enumerate(operation_ids, 1):
                        cursor.execute(
                            f"UPDATE {table_name} SET sequence_order = %s WHERE id = %s AND job_id = %s",
                            [i + max_sequence, operation_id, job.id]
                        )
                    
                    # Now set the correct sequence orders
                    for i, operation_id in enumerate(operation_ids, 1):
                        cursor.execute(
                            f"UPDATE {table_name} SET sequence_order = %s WHERE id = %s AND job_id = %s",
                            [i, operation_id, job.id]
                        )
                        
            except Exception as e:
                # Fallback: Delete and recreate approach
                print(f"Raw SQL approach failed: {e}, trying delete/recreate approach")
                
                # Store all operation data
                operations_data = []
                for operation in job_operations:
                    operations_data.append({
                        'operation_id': operation.operation_id,
                        'operation_name': operation.operation_name,
                        'makeready_price': operation.makeready_price,
                        'price_per_sheet': operation.price_per_sheet,
                        'plate_price': operation.plate_price,
                        'makeready_time_minutes': operation.makeready_time_minutes,
                        'cleaning_time_minutes': operation.cleaning_time_minutes,
                        'sheets_per_minute': operation.sheets_per_minute,
                        'quantity_before': operation.quantity_before,
                        'quantity_after': operation.quantity_after,
                        'waste_sheets': operation.waste_sheets,
                        'processing_quantity': operation.processing_quantity,
                        'total_cost': operation.total_cost,
                        'total_time_minutes': operation.total_time_minutes,
                        'colors_used': operation.colors_used,
                    })
                
                # Create lookup for operation data by ID
                data_lookup = {op.id: data for op, data in zip(job_operations, operations_data)}
                
                # Delete all existing operations for this job
                JobOperation.objects.filter(job=job).delete()
                
                # Recreate operations in the new order
                for sequence, operation_id in enumerate(operation_ids, 1):
                    if operation_id in data_lookup:
                        data = data_lookup[operation_id]
                        JobOperation.objects.create(
                            job=job,
                            operation_id=data['operation_id'],
                            sequence_order=sequence,
                            operation_name=data['operation_name'],
                            makeready_price=data['makeready_price'],
                            price_per_sheet=data['price_per_sheet'],
                            plate_price=data['plate_price'],
                            makeready_time_minutes=data['makeready_time_minutes'],
                            cleaning_time_minutes=data['cleaning_time_minutes'],
                            sheets_per_minute=data['sheets_per_minute'],
                            quantity_before=data['quantity_before'],
                            quantity_after=data['quantity_after'],
                            waste_sheets=data['waste_sheets'],
                            processing_quantity=data['processing_quantity'],
                            total_cost=data['total_cost'],
                            total_time_minutes=data['total_time_minutes'],
                            colors_used=data['colors_used'],
                        )