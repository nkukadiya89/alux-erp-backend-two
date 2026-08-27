from django.db.models.signals import post_save
from django.dispatch import receiver

from die_requisition.models import DieRequisition
from utils.generate_number import generate_die_requisition_no

from .models import Planning


@receiver(post_save, sender=Planning)
def create_die_requisition_for_planning(sender, instance, created, **kwargs):
    if created and not instance.die_requisition:
        die_req = DieRequisition.objects.create(
            requisition_no=generate_die_requisition_no(),
            requisition_date=instance.planning_date,
            workorder_no=instance.workorder,
            customer=instance.workorder.bill_to if instance.workorder else None,
            priority="Normal",
            required_date=instance.scheduled_date,
            status="Requested",
            remarks=f"Auto-generated from Planning {instance.planning_no}",
            created_by=instance.created_by,
        )

        Planning.objects.filter(pk=instance.pk).update(die_requisition=die_req)
