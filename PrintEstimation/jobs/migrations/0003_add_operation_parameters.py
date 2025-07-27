# Generated manually to add operation_parameters field to JobOperation

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0002_remove_variant_quantities'),
    ]

    operations = [
        migrations.AddField(
            model_name='joboperation',
            name='operation_parameters',
            field=models.JSONField(blank=True, help_text="Dynamic parameters for this operation (e.g., {'cut_pieces': 4, 'fold_count': 2})", null=True),
        ),
    ]