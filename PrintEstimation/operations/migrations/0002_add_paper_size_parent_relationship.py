# Generated migration for adding parent size relationship to PaperSize

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='papersize',
            name='parent_size',
            field=models.ForeignKey(blank=True, help_text='Parent size this size is cut from', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='child_sizes', to='operations.papersize'),
        ),
        migrations.AddField(
            model_name='papersize',
            name='parts_of_parent',
            field=models.PositiveIntegerField(default=1, help_text='How many parts this size makes from parent size (e.g., 4 for quarter size)'),
        ),
    ]