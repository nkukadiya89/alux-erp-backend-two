from django.db import migrations


def restore_mechanical_test_always(apps, schema_editor):
    """
    Mechanical Test is always in the process:
    - with Ageing: ... → Dimension → Ageing → Mechanical Test
    - without Ageing: ... → Dimension → Mechanical Test
    Resync restores soft-deleted MECHANICAL_TEST rows on non-ageing tracks.
    """
    from workorder.process_tracking import resync_all_jobwork_stages

    resync_all_jobwork_stages(user=None)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workorder", "0031_mechanical_test_after_ageing_only"),
    ]

    operations = [
        migrations.RunPython(restore_mechanical_test_always, noop_reverse),
    ]
