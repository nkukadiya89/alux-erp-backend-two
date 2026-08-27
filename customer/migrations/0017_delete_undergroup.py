# Generated manually to remove UnderGroup model

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("customer", "0016_alter_accountgroup_created_by_and_more"),
    ]

    operations = [
        migrations.DeleteModel(
            name="UnderGroup",
        ),
    ]
