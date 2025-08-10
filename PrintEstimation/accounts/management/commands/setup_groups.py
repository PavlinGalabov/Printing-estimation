"""
Management command to set up admin groups and permissions.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from PrintEstimation.accounts.models import User, Client
from PrintEstimation.jobs.models import Job, JobOperation, JobVariant
from PrintEstimation.operations.models import Operation, OperationCategory, PaperType, PaperSize


class Command(BaseCommand):
    help = 'Set up admin groups with appropriate permissions'

    def handle(self, *args, **options):
        self.stdout.write('Setting up admin groups...')

        # Create groups
        staff_group, created = Group.objects.get_or_create(name='Staff')
        if created:
            self.stdout.write(self.style.SUCCESS('Created Staff group'))
        else:
            self.stdout.write('Staff group already exists')

        managers_group, created = Group.objects.get_or_create(name='Managers')
        if created:
            self.stdout.write(self.style.SUCCESS('Created Managers group'))
        else:
            self.stdout.write('Managers group already exists')

        # Clear existing permissions
        staff_group.permissions.clear()
        managers_group.permissions.clear()

        # Get content types
        user_ct = ContentType.objects.get_for_model(User)
        client_ct = ContentType.objects.get_for_model(Client)
        job_ct = ContentType.objects.get_for_model(Job)
        job_operation_ct = ContentType.objects.get_for_model(JobOperation)
        job_variant_ct = ContentType.objects.get_for_model(JobVariant)
        operation_ct = ContentType.objects.get_for_model(Operation)
        operation_category_ct = ContentType.objects.get_for_model(OperationCategory)
        paper_type_ct = ContentType.objects.get_for_model(PaperType)
        paper_size_ct = ContentType.objects.get_for_model(PaperSize)

        # Staff permissions (limited CRUD)
        staff_permissions = [
            # Jobs - can view all, create, edit own
            Permission.objects.get(codename='view_job', content_type=job_ct),
            Permission.objects.get(codename='add_job', content_type=job_ct),
            Permission.objects.get(codename='change_job', content_type=job_ct),
            
            # Clients - full CRUD
            Permission.objects.get(codename='view_client', content_type=client_ct),
            Permission.objects.get(codename='add_client', content_type=client_ct),
            Permission.objects.get(codename='change_client', content_type=client_ct),
            
            # Operations - view only
            Permission.objects.get(codename='view_operation', content_type=operation_ct),
            Permission.objects.get(codename='view_operationcategory', content_type=operation_category_ct),
            Permission.objects.get(codename='view_papertype', content_type=paper_type_ct),
            Permission.objects.get(codename='view_papersize', content_type=paper_size_ct),
            
            # Job Operations and Variants - can modify
            Permission.objects.get(codename='view_joboperation', content_type=job_operation_ct),
            Permission.objects.get(codename='add_joboperation', content_type=job_operation_ct),
            Permission.objects.get(codename='change_joboperation', content_type=job_operation_ct),
            Permission.objects.get(codename='view_jobvariant', content_type=job_variant_ct),
            Permission.objects.get(codename='add_jobvariant', content_type=job_variant_ct),
            Permission.objects.get(codename='change_jobvariant', content_type=job_variant_ct),
        ]

        # Managers permissions (full CRUD)
        manager_permissions = [
            # Users - view and edit (not delete)
            Permission.objects.get(codename='view_user', content_type=user_ct),
            Permission.objects.get(codename='change_user', content_type=user_ct),
            
            # Jobs - full CRUD
            Permission.objects.get(codename='view_job', content_type=job_ct),
            Permission.objects.get(codename='add_job', content_type=job_ct),
            Permission.objects.get(codename='change_job', content_type=job_ct),
            Permission.objects.get(codename='delete_job', content_type=job_ct),
            
            # Clients - full CRUD
            Permission.objects.get(codename='view_client', content_type=client_ct),
            Permission.objects.get(codename='add_client', content_type=client_ct),
            Permission.objects.get(codename='change_client', content_type=client_ct),
            Permission.objects.get(codename='delete_client', content_type=client_ct),
            
            # Operations - full CRUD
            Permission.objects.get(codename='view_operation', content_type=operation_ct),
            Permission.objects.get(codename='add_operation', content_type=operation_ct),
            Permission.objects.get(codename='change_operation', content_type=operation_ct),
            Permission.objects.get(codename='delete_operation', content_type=operation_ct),
            
            Permission.objects.get(codename='view_operationcategory', content_type=operation_category_ct),
            Permission.objects.get(codename='add_operationcategory', content_type=operation_category_ct),
            Permission.objects.get(codename='change_operationcategory', content_type=operation_category_ct),
            
            Permission.objects.get(codename='view_papertype', content_type=paper_type_ct),
            Permission.objects.get(codename='add_papertype', content_type=paper_type_ct),
            Permission.objects.get(codename='change_papertype', content_type=paper_type_ct),
            
            Permission.objects.get(codename='view_papersize', content_type=paper_size_ct),
            Permission.objects.get(codename='add_papersize', content_type=paper_size_ct),
            Permission.objects.get(codename='change_papersize', content_type=paper_size_ct),
            
            # Job Operations and Variants - full CRUD
            Permission.objects.get(codename='view_joboperation', content_type=job_operation_ct),
            Permission.objects.get(codename='add_joboperation', content_type=job_operation_ct),
            Permission.objects.get(codename='change_joboperation', content_type=job_operation_ct),
            Permission.objects.get(codename='delete_joboperation', content_type=job_operation_ct),
            
            Permission.objects.get(codename='view_jobvariant', content_type=job_variant_ct),
            Permission.objects.get(codename='add_jobvariant', content_type=job_variant_ct),
            Permission.objects.get(codename='change_jobvariant', content_type=job_variant_ct),
            Permission.objects.get(codename='delete_jobvariant', content_type=job_variant_ct),
        ]

        # Assign permissions
        staff_group.permissions.set(staff_permissions)
        managers_group.permissions.set(manager_permissions)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully set up groups:\n'
                f'- Staff: {len(staff_permissions)} permissions\n'
                f'- Managers: {len(manager_permissions)} permissions'
            )
        )

        # Update user types to match groups
        self.stdout.write('Updating user types...')
        
        # Update existing staff users
        staff_users = User.objects.filter(user_type='staff')
        for user in staff_users:
            user.groups.add(staff_group)
            if not user.is_staff:
                user.is_staff = True
                user.save()
        
        self.stdout.write(f'Updated {staff_users.count()} staff users')
        
        # Create a sample manager if none exist
        if not User.objects.filter(user_type='staff', is_superuser=False).exists():
            self.stdout.write('Consider creating manager users and adding them to the Managers group')
        
        self.stdout.write(self.style.SUCCESS('Group setup completed!'))