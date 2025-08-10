# Generated migration for JobPDFExport model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0007_job_total_cost'),
    ]

    operations = [
        migrations.CreateModel(
            name='JobPDFExport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('export_type', models.CharField(choices=[('estimate', 'Estimate/Quote'), ('invoice', 'Invoice'), ('job_sheet', 'Job Sheet'), ('technical_specs', 'Technical Specifications')], max_length=20)),
                ('file_name', models.CharField(max_length=255)),
                ('file_path', models.FileField(upload_to='exports/pdfs/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('file_size', models.PositiveIntegerField(default=0)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pdf_exports', to='jobs.job')),
            ],
            options={
                'verbose_name': 'Job PDF Export',
                'verbose_name_plural': 'Job PDF Exports',
                'ordering': ['-created_at'],
            },
        ),
    ]