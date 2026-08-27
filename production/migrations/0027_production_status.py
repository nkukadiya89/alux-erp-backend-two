from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0026_production_completion_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="production",
            name="status",
            field=models.CharField(
                choices=[("DRAFT", "Draft"), ("SUBMITTED", "Submitted")],
                db_index=True,
                default="SUBMITTED",
                help_text="DRAFT = production started (incomplete output); SUBMITTED = final submit",
                max_length=20,
            ),
        ),
    ]
