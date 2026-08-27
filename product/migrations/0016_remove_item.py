# Generated manually to remove Item model

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("product", "0015_alter_temper_name"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Item",
        ),
    ]
