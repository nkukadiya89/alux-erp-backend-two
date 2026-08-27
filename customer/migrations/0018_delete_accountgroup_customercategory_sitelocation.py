# Generated manually to remove AccountGroup, CustomerCategory, BillingPerson, ShipingPerson, and SiteLocation models

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("customer", "0017_delete_undergroup"),
    ]

    operations = [
        migrations.DeleteModel(
            name="BillingPerson",
        ),
        migrations.DeleteModel(
            name="ShipingPerson",
        ),
        migrations.DeleteModel(
            name="SiteLocation",
        ),
        migrations.DeleteModel(
            name="AccountGroup",
        ),
        migrations.DeleteModel(
            name="CustomerCategory",
        ),
    ]
