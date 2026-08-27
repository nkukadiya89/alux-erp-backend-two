from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inquiry_quotation", "0007_inquiryquotationdetail_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="inquiryquotation",
            name="revision_number",
            field=models.IntegerField(default=0),
        ),
        migrations.AddConstraint(
            model_name="inquiryquotation",
            constraint=models.UniqueConstraint(
                fields=["quotation_no", "revision_number"],
                name="unique_quotation_revision",
            ),
        ),
    ]
