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
    Implements formula-based approach with sequential operations.
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
            operation_result = self._calculate_operation(job_operation.operation, job_operation)

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


        return {
            'success': True,
            'job': self.job,
            'operations': self.operations_data,
            'total_cost': self.total_cost,
            'total_time_minutes': self.total_time,
            'total_time_formatted': self._format_time(self.total_time)
        }

    def _calculate_paper_requirements(self):
        """Calculate paper requirements based on job parameters and operation waste."""
        # Calculate print run (quantity / n_up)
        print_run = self.job.quantity // self.job.n_up
        if self.job.quantity % self.job.n_up > 0:
            print_run += 1  # Round up for partial sheets

        # Calculate total waste needed by simulating all operations
        total_waste_needed = self._estimate_total_waste(print_run)
        
        # Total printing sheets needed
        total_printing_sheets = print_run + total_waste_needed
        
        # Parent sheets to buy = printing sheets / parts_of_selling_size (rounded up)
        sheets_to_buy = total_printing_sheets // self.job.parts_of_selling_size
        if total_printing_sheets % self.job.parts_of_selling_size > 0:
            sheets_to_buy += 1  # Round up for partial parent sheets

        # Calculate paper weight
        paper_area_m2 = self.job.selling_size.area_m2
        paper_weight_kg = (
            Decimal(str(paper_area_m2)) *
            Decimal(str(self.job.paper_type.weight_gsm)) *
            Decimal(str(sheets_to_buy)) / 1000
        )

        # Calculate paper cost
        paper_cost = paper_weight_kg * self.job.paper_type.price_per_kg

        # Update job with calculated values
        self.job.print_run = print_run
        self.job.waste_sheets = total_waste_needed
        self.job.sheets_to_buy = sheets_to_buy
        self.job.paper_weight_kg = paper_weight_kg
        self.job.paper_cost = paper_cost
        self.job.save()

    def _estimate_total_waste(self, target_quantity):
        """Estimate total waste needed across all operations to end with target quantity."""
        job_operations = self.job.job_operations.all().order_by('sequence_order')
        
        if not job_operations.exists():
            # No operations, use basic 5% waste
            return int(target_quantity * 0.05)
        
        # Work backwards from target quantity to estimate starting quantity needed
        current_quantity = target_quantity
        
        # Reverse through operations to estimate required input quantities
        for operation in reversed(job_operations):
            # Estimate waste this operation will produce
            job_params = {
                'quantity': self.job.quantity,
                'n_up': self.job.n_up,
                'colors_front': self.job.colors_front,
                'colors_back': self.job.colors_back,
                'print_run': target_quantity,
                'current_quantity': current_quantity,
                'paper_weight_kg': 0,  # Not needed for waste estimation
            }
            
            # Calculate waste for this operation (access Operation model attributes)
            op = operation.operation  # Get the related Operation model
            waste_sheets = 0
            if op.base_waste_sheets > 0 or op.waste_percentage > 0:
                if op.uses_colors:
                    total_colors = job_params['colors_front'] + job_params['colors_back']
                    waste_sheets = total_colors * (
                        op.base_waste_sheets +
                        float(op.waste_percentage) * job_params['print_run']
                    )
                else:
                    waste_sheets = (
                        op.base_waste_sheets +
                        float(op.waste_percentage) * job_params['print_run']
                    )
                waste_sheets = int(waste_sheets)
            
            # Add waste to get input quantity needed for this operation
            current_quantity += waste_sheets
            
            # Apply reverse multipliers/dividers
            if op.divides_quantity_by > 1:
                current_quantity *= op.divides_quantity_by
            elif op.multiplies_quantity_by > 1:
                current_quantity = current_quantity // op.multiplies_quantity_by
        
        # Total waste is the difference between starting and target quantities
        return max(0, current_quantity - target_quantity)

    def _calculate_operation(self, operation, job_operation=None):
        """
        Calculate cost and time for a single operation using formulas.

        Args:
            operation: Operation model instance
            job_operation: JobOperation instance with dynamic parameters (optional)

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

            # Get dynamic operation parameters if available
            operation_parameters = {}
            if job_operation and job_operation.operation_parameters:
                operation_parameters = job_operation.operation_parameters

            # Use the operation's built-in calculation methods
            cost_result = operation.calculate_cost(job_params, operation_parameters)
            time_minutes = operation.calculate_time(job_params, operation_parameters)

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
                'formula': f"{total_colors} colors × (€{operation.makeready_price} makeready + €{operation.plate_price} plate + {cost_result['processing_quantity']} sheets × €{operation.price_per_sheet})"
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
        # Operations cost is what we calculated in self.total_cost
        operations_cost = self.total_cost
        paper_cost = self.job.paper_cost or Decimal('0')
        
        # Store operations cost for reference and total material cost
        self.job.total_material_cost = operations_cost + paper_cost
        self.job.total_labor_cost = Decimal('0')
        self.job.total_outsourcing_cost = Decimal('0')
        self.job.total_cost = self.job.total_material_cost + self.job.total_labor_cost + self.job.total_outsourcing_cost
        self.job.total_time_minutes = self.total_time
        self.job.status = 'calculated'
        self.job.calculated_at = timezone.now()
        self.job.save()


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

    def calculate_variant(self, quantity):
        """
        Calculate cost and time for a specific quantity variant.
        Returns calculation data without saving to database.
        """
        # Store original job quantity and calculated values
        original_quantity = self.job.quantity
        original_print_run = self.job.print_run
        original_sheets_to_buy = self.job.sheets_to_buy
        original_paper_weight = self.job.paper_weight_kg
        original_paper_cost = self.job.paper_cost
        original_total_material_cost = self.job.total_material_cost
        original_total_cost = self.job.total_cost
        
        try:
            # Temporarily set the job quantity to the variant quantity
            self.job.quantity = quantity
            
            # Recalculate paper requirements for this quantity
            self._calculate_paper_requirements()
            
            # Process operations with the new quantity
            job_operations = self.job.job_operations.all().order_by('sequence_order')
            
            if not job_operations.exists():
                return {
                    'success': False,
                    'error': 'No operations defined for this job.'
                }
            
            # Reset calculation state
            self.current_quantity = self.job.sheets_to_buy
            self.total_cost = Decimal('0')
            self.total_time = 0
            self.operations_data = []
            
            # Process each operation
            for job_operation in job_operations:
                result = self._calculate_operation(job_operation.operation, job_operation)
                
                if not result['success']:
                    return result
                
                # Update running totals
                self.total_cost += result['total_cost']
                self.total_time += result['total_time_minutes']
                self.current_quantity = result['quantity_after']
                
                # Store operation data
                self.operations_data.append({
                    'operation': job_operation.operation,
                    'operation_name': job_operation.operation_name,
                    'sequence_order': job_operation.sequence_order,
                    **result
                })
            
            # Calculate paper cost (use the job's calculated paper_cost)
            paper_cost = self.job.paper_cost or Decimal('0')
            
            # Operations cost is what we calculated in self.total_cost
            operations_cost = self.total_cost
            
            # Total cost is operations + paper
            total_cost = operations_cost + paper_cost
            
            return {
                'success': True,
                'quantity': quantity,
                'total_cost': total_cost,
                'paper_cost': paper_cost,
                'operations_cost': operations_cost,
                'total_time_minutes': self.total_time,
                'print_run': self.job.print_run,
                'waste_sheets': self.job.waste_sheets,
                'sheets_to_buy': self.job.sheets_to_buy,
                'paper_weight_kg': self.job.paper_weight_kg,
                'operations_data': self.operations_data,
                'cost_per_piece': total_cost / quantity if quantity > 0 else Decimal('0')
            }
            
        finally:
            # Always restore original values
            self.job.quantity = original_quantity
            self.job.print_run = original_print_run
            self.job.sheets_to_buy = original_sheets_to_buy
            self.job.paper_weight_kg = original_paper_weight
            self.job.paper_cost = original_paper_cost
            self.job.total_material_cost = original_total_material_cost
            self.job.total_cost = original_total_cost

    def calculate_all_variants(self, quantities):
        """
        Calculate multiple quantity variants and save them to the database.
        
        Args:
            quantities: List of quantities to calculate
            
        Returns:
            Dictionary with success status and created variants
        """
        if not quantities:
            return {
                'success': False,
                'error': 'No quantities provided'
            }
        
        try:
            # Clear existing variants
            self.job.variants.all().delete()
            
            created_variants = []
            failed_calculations = []
            
            for quantity in quantities:
                # Calculate this variant
                result = self.calculate_variant(quantity)
                
                if result['success']:
                    # Create JobVariant record
                    variant = JobVariant.objects.create(
                        job=self.job,
                        quantity=quantity,
                        total_cost=result['total_cost'],
                        paper_cost=result['paper_cost'],
                        operations_cost=result['operations_cost'],
                        total_time_minutes=result['total_time_minutes'],
                        print_run=result['print_run'],
                        waste_sheets=result['waste_sheets'],
                        sheets_to_buy=result['sheets_to_buy'],
                        paper_weight_kg=result['paper_weight_kg']
                    )
                    created_variants.append(variant)
                else:
                    failed_calculations.append({
                        'quantity': quantity,
                        'error': result.get('error', 'Unknown error')
                    })
            
            return {
                'success': True,
                'created_variants': created_variants,
                'failed_calculations': failed_calculations,
                'message': f'Successfully calculated {len(created_variants)} variants'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error calculating variants: {str(e)}'
            }


class JobOperationManager:
    """
    Service for managing operations within a job.
    """

    @staticmethod
    def add_operation(job, operation, sequence_order=None):
        """Add an operation to a job."""
        from django.db import transaction
        
        with transaction.atomic():
            # Lock the job to prevent race conditions
            job = Job.objects.select_for_update().get(pk=job.pk)
            
            if sequence_order is None:
                # Add at the end - get current max sequence order
                max_sequence = job.job_operations.aggregate(
                    max_seq=models.Max('sequence_order')
                )['max_seq']
                sequence_order = (max_sequence or 0) + 1

            # Shift existing operations if inserting in middle
            current_count = job.job_operations.count()
            if sequence_order <= current_count:
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