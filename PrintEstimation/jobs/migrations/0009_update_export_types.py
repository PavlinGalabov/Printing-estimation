# Migration to update export types

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0008_add_pdf_export_model'),
    ]

    operations = [
        # Remove any exports with unsupported types
        migrations.RunSQL(
            "DELETE FROM jobs_jobpdfexport WHERE export_type NOT IN ('estimate', 'job_sheet');",
            reverse_sql=migrations.RunSQL.noop
        ),
    ]