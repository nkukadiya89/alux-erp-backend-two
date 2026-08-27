# import csv
# import os
# from datetime import datetime
# from decimal import Decimal
# from os import path
# from material.models import Material
# from transporter.models import Transporter
# from vehicle_master.models import VehicleMaster
# from vehicle_type.models import VehicleType
# from decouple import config
# from django.conf import settings
# from django.contrib.auth.models import Permission
# from django.core.management.base import BaseCommand
# from django.utils import timezone

# from aging.models import AgingCycle
# from common.models import (
#     Country,
#     Currency,
#     FinancialYearModel,
#     GstType,
#     ItemCategory,
#     Plant,
#     SectionType,
#     Department,
#     YieldUnit,
# )
# from die.models import Die, DieCategory, DieGroup
# from product.models import Alloy, Temper
# from user.models import CustomGroup, User


# class Command(BaseCommand):
#     help = "Initial setup: creates superuser."

#     def add_arguments(self, parser) -> None:
#         parser.add_argument("--country", type=bool, help="Country data to be uploaded")
#         parser.add_argument(
#             "--currency", type=bool, help="Currency data to be uploaded"
#         )

#         parser.add_argument("--groups", type=bool, help="Create Groups")
#         parser.add_argument("--user", type=bool, help="Create Super User")
#         parser.add_argument(
#             "--vehicletype", type=bool, help="vehicletype data to be uploaded"
#         )
#         parser.add_argument(
#             "--vehiclemaster", type=bool, help="vehiclemaster data to be uploaded"
#         )
#         parser.add_argument(
#             "--material", type=bool, help="Material data to be uploaded"
#         )
#         parser.add_argument(
#             "--transporter", type=bool, help="Transporter data to be uploaded"
#         )
#         parser.add_argument(
#             "--sectiontype", type=bool, help="Section Type data to be uploaded"
#         )
#         parser.add_argument(
#             "--department", type=bool, help="Department data to be uploaded"
#         )
#         parser.add_argument(
#             "--itemcategory", type=bool, help="Item Category data to be uploaded"
#         )

#     def handle(self, *args, **kwargs):
#         self.stdout.write("Initialise..")

#         if (
#             kwargs["country"] is None
#             and kwargs["user"] is None
#             and kwargs["currency"] is None
#             and kwargs["groups"] is None
#             and kwargs["vehicletype"] is None
#             and kwargs["vehiclemaster"] is None
#             and kwargs["material"] is None
#             and kwargs["transporter"] is None
#             and kwargs["sectiontype"] is None
#             and kwargs["department"] is None
#             and kwargs["itemcategory"] is None
#         ):
#             self.load_financial_data()
#             self.load_country()
#             self.create_superuser()
#             self.load_transporter()
#             self.load_material()
#             self.load_currency()
#             # self.load_vehiclemaster()
#             self.load_vehicletype()
#             self.create_custom_groups()
#             self.load_financial_data()
#             self.load_die_group()
#             # self.load_alloy_data()
#             self.load_temper_data()
#             self.load_aging_cycle_data()
#             self.load_gst_type_data()
#             self.load_die_category()
#             self.load_die()
#             self.load_section_type()
#             self.load_department()
#             self.load_yield_unit()

#         if kwargs["user"]:
#             self.create_superuser()

#         if kwargs["groups"]:
#             self.create_custom_groups()

#         if kwargs["currency"]:
#             self.load_currency()

#         if kwargs["country"]:
#             self.load_country()

#         if kwargs["vehicletype"]:
#             self.load_vehicletype()

#         if kwargs["vehiclemaster"]:
#             self.load_vehiclemaster()

#         if kwargs["material"]:
#             self.load_material()

#         if kwargs["transporter"]:
#             self.load_transporter()

#         if kwargs["sectiontype"]:
#             self.load_section_type()

#         if kwargs["department"]:
#             self.load_department()

#         if kwargs["itemcategory"]:
#             self.load_item_category()

#     def create_superuser(self):
#         """Create superuser"""

#         if not len(User.objects.filter(is_superuser=True)) > 0:
#             email = config("INIT_EMAIL")
#             password = config("ADMIN_PASSWORD")
#             user = User.objects.create(email=email, username="Alux_admin")
#             user.set_password(password)  # type: ignore
#             user.is_superuser = True
#             user.is_staff = True
#             user.is_active = True
#             user.first_name = "Alux"
#             user.last_name = "Admin"
#             user.status = "active"
#             user.save()
#             group, created = CustomGroup.objects.get_or_create(name="Super Admin")
#             group.user_set.add(user)
#             self.stdout.write("Super User Created!.......")
#             return user

#     # def create_groups(self):
#     def create_custom_groups(self):
#         self.stdout.write("Creating Groups.......")
#         super_admin_group, _ = CustomGroup.objects.get_or_create(name="Super Admin")
#         design_manager_group, _ = CustomGroup.objects.get_or_create(
#             name="Design Manager"
#         )
#         sm_manager_group, _ = CustomGroup.objects.get_or_create(name="SM Manager")
#         planning_manager_group, _ = CustomGroup.objects.get_or_create(
#             name="Planning Manager"
#         )
#         dispatch_manager_group, _ = CustomGroup.objects.get_or_create(
#             name="Dispatch Manager"
#         )
#         warehouse_manager_group, _ = CustomGroup.objects.get_or_create(
#             name="Warehouse Manager"
#         )

#         self.stdout.write("Groups Created!.......")

#         super_admin_permissions = [
#             "user|Can add custom group",
#             "user|Can change custom group",
#             "user|Can delete custom group",
#             "user|Can view custom group",
#             "user|Can add user",
#             "user|Can change user",
#             "user|Can delete user",
#             "user|Can view user",
#             "user|Can add user profile",
#             "user|Can change user profile",
#             "user|Can delete user profile",
#             "user|Can view user profile",
#             "user|Can add auth group model",
#             "user|Can change auth group model",
#             "user|Can delete auth group model",
#             "user|Can view auth group model",
#             "user|Can add auth group permissions model",
#             "user|Can change auth group permissions model",
#             "user|Can delete auth group permissions model",
#             "user|Can view auth group permissions model",
#             "user|Can add auth permission model",
#             "user|Can change auth permission model",
#             "user|Can view auth permission model",
#             "user|Can delete auth permission model",
#             "user|Can add user groups model",
#             "user|Can change user groups model",
#             "user|Can delete user groups model",
#             "user|Can view user groups model",
#             "aging|Can add aging cycle",
#             "aging|Can change aging cycle",
#             "aging|Can delete aging cycle",
#             "aging|Can view aging cycle",
#             "bundle_inward|Can add bundle inward",
#             "bundle_inward|Can change bundle inward",
#             "bundle_inward|Can delete bundle inward",
#             "bundle_inward|Can view bundle inward",
#             "bundle_inward|Can add excess stock",
#             "bundle_inward|Can change excess stock",
#             "bundle_inward|Can delete excess stock",
#             "bundle_inward|Can view excess stock",
#             "bundle_outward|Can add bundle outward",
#             "bundle_outward|Can change bundle outward",
#             "bundle_outward|Can delete bundle outward",
#             "bundle_outward|Can view bundle outward",
#             "bundle_outward|Can add bundle outward details",
#             "bundle_outward|Can change bundle outward details",
#             "bundle_outward|Can delete bundle outward details",
#             "bundle_outward|Can view bundle outward details",
#             "die_quotation|Can add die quotation",
#             "die_quotation|Can change die quotation",
#             "die_quotation|Can delete die quotation",
#             "die_quotation|Can view die quotation",
#             "die_quotation|Can add die quotation details",
#             "die_quotation|Can change die quotation details",
#             "die_quotation|Can delete die quotation details",
#             "die_quotation|Can view die quotation details",
#             "planning|Can add planning",
#             "planning|Can change planning",
#             "planning|Can delete planning",
#             "planning|Can view planning",
#             "proforma|Can add proforma",
#             "proforma|Can change proforma",
#             "proforma|Can delete proforma",
#             "proforma|Can view proforma",
#             "proforma|Can add proforma details",
#             "proforma|Can change proforma details",
#             "proforma|Can delete proforma details",
#             "proforma|Can view proforma details",
#             "bloster|Can add bloster master",
#             "bloster|Can change bloster master",
#             "bloster|Can delete bloster master",
#             "bloster|Can view bloster master",
#             "common|Can add country",
#             "common|Can change country",
#             "common|Can delete country",
#             "common|Can view country",
#             "common|Can add currency",
#             "common|Can change currency",
#             "common|Can delete currency",
#             "common|Can view currency",
#             "common|Can add financial year model",
#             "common|Can change financial year model",
#             "common|Can delete financial year model",
#             "common|Can view financial year model",
#             "common|Can add packing type",
#             "common|Can change packing type",
#             "common|Can delete packing type",
#             "common|Can view packing type",
#             "customer|Can add account group",
#             "customer|Can change account group",
#             "customer|Can delete account group",
#             "customer|Can view account group",
#             "customer|Can add banking details",
#             "customer|Can change banking details",
#             "customer|Can delete banking details",
#             "customer|Can view banking details",
#             "customer|Can add billing person",
#             "customer|Can change billing person",
#             "customer|Can delete billing person",
#             "customer|Can view billing person",
#             "customer|Can add contact person",
#             "customer|Can change contact person",
#             "customer|Can delete contact person",
#             "customer|Can view contact person",
#             "customer|Can add customer",
#             "customer|Can change customer",
#             "customer|Can delete customer",
#             "customer|Can view customer",
#             "customer|Can add customer category",
#             "customer|Can change customer category",
#             "customer|Can delete customer category",
#             "customer|Can view customer category",
#             "customer|Can add customer type",
#             "customer|Can change customer type",
#             "customer|Can delete customer type",
#             "customer|Can view customer type",
#             "customer|Can add site location",
#             "customer|Can change site location",
#             "customer|Can delete site location",
#             "customer|Can view site location",
#             "customer|Can add under group",
#             "customer|Can change under group",
#             "customer|Can delete under group",
#             "customer|Can view under group",
#             "die|Can add conversion rate",
#             "die|Can change conversion rate",
#             "die|Can delete conversion rate",
#             "die|Can view conversion rate",
#             "die|Can add die",
#             "die|Can change die",
#             "die|Can delete die",
#             "die|Can view die",
#             "die|Can add die category",
#             "die|Can change die category",
#             "die|Can delete die category",
#             "die|Can view die category",
#             "die|Can add die group",
#             "die|Can change die group",
#             "die|Can delete die group",
#             "die|Can view die group",
#             "die|Can add die press",
#             "die|Can change die press",
#             "die|Can delete die press",
#             "die|Can view die press",
#             "die|Can add die size",
#             "die|Can change die size",
#             "die|Can delete die size",
#             "die|Can view die size",
#             "die|Can add die sub category",
#             "die|Can change die sub category",
#             "die|Can delete die sub category",
#             "die|Can view die sub category",
#             "die|Can add die tool",
#             "die|Can change die tool",
#             "die|Can delete die tool",
#             "die|Can view die tool",
#             "die|Can add die type",
#             "die|Can change die type",
#             "die|Can delete die type",
#             "die|Can view die type",
#             "nalco|Can add nalco master",
#             "nalco|Can change nalco master",
#             "nalco|Can delete nalco master",
#             "nalco|Can view nalco master",
#             "product|Can add alloy",
#             "product|Can change alloy",
#             "product|Can delete alloy",
#             "product|Can view alloy",
#             "product|Can add item",
#             "product|Can change item",
#             "product|Can delete item",
#             "product|Can view item",
#             "product|Can add temper",
#             "product|Can change temper",
#             "product|Can delete temper",
#             "product|Can view temper",
#             "quotation|Can add quotation",
#             "quotation|Can change quotation",
#             "quotation|Can delete quotation",
#             "quotation|Can view quotation",
#             "quotation|Can add quotation detail",
#             "quotation|Can change quotation detail",
#             "quotation|Can delete quotation detail",
#             "quotation|Can view quotation detail",
#             "vendor|Can add bank details",
#             "vendor|Can change bank details",
#             "vendor|Can delete bank details",
#             "vendor|Can view bank details",
#             "vendor|Can add key persons",
#             "vendor|Can change key persons",
#             "vendor|Can delete key persons",
#             "vendor|Can view key persons",
#             "vendor|Can add vendor",
#             "vendor|Can change vendor",
#             "vendor|Can delete vendor",
#             "vendor|Can view vendor",
#             "workorder|Can add work order",
#             "workorder|Can change work order",
#             "workorder|Can delete work order",
#             "workorder|Can view work order",
#             "workorder|Can add work order detail",
#             "workorder|Can change work order detail",
#             "workorder|Can delete work order detail",
#             "workorder|Can view work order detail",
#             "workorder|Can print production copy",
#             "workorder|Can print packing copy",
#             "workorder|Can print account sales copy",
#             "workorder|Can print workorder copy",
#             "die|Can print profile",
#             "die|Can print profile workorder report",
#             "die|Can download profile PDF",
#             "die|Can download profile Excel",
#             "die|Can download profile tool PDF",
#             "die|Can download profile tool Excel",
#             "die|Can download profile category PDF",
#             "die|Can download profile category Excel",
#             "die|Can download profile group PDF",
#             "die|Can download profile group Excel",
#             "die|Can download profile press PDF",
#             "die|Can download profile press Excel",
#             "die|Can download profile size PDF",
#             "die|Can download profile size Excel",
#             "die|Can download profile sub category PDF",
#             "die|Can download profile sub category Excel",
#             "bolster|Can download bolster PDF",
#             "bolster|Can download bolster Excel",
#             "vendor|Can download vendor PDF",
#             "vendor|Can download vendor Excel",
#             "customer|Can download under group PDF",
#             "customer|Can download under group Excel",
#             "customer|Can download account group PDF",
#             "customer|Can download account group Excel",
#             "customer|Can download customer category PDF",
#             "customer|Can download customer category Excel",
#             "customer|Can download customer type PDF",
#             "customer|Can download customer type Excel",
#             "customer|Can print customer workorder report",
#             "customer|Can download customer PDF",
#             "customer|Can download customer Excel",
#             "customer|Can download site location PDF",
#             "customer|Can download site location Excel",
#             "die|Can download conversion rate PDF",
#             "die|Can download conversion rate Excel",
#             "product|Can download alloy PDF",
#             "product|Can download alloy Excel",
#             "product|Can download temper PDF",
#             "product|Can download temper Excel",
#             "nalco|Can download nalco rate PDF",
#             "nalco|Can download nalco rate Excel",
#             "quotation|Can print quotation",
#             "die_quotation|Can print die quotation",
#             "proforma|Can print proforma",
#             "proforma|Can print proforma copy",
#             "bundle_inward|Can print bundle inward",
#             "bundle_inward|Can download bundle inward Excel",
#             "bundle_inward|Can print current stock",
#             "bundle_inward|Can download current stock Excel",
#             "bundle_inward|Can print excess stock",
#             "bundle_inward|Can download excess stock Excel",
#             "bundle_outward|Can print bundle outward",
#             "bundle_outward|Can download bundle outward Excel",
#             "bundle_verification|Can print stock verification",
#             "bundle_verification|Can print dispatch verification",
#             "planning|Can download planning PDF",
#             "planning|Can download planning Excel",
#             "planning|Can download planning priority PDF",
#             "planning|Can download planning priority Excel",
#             "warehouse|Can print warehouse bundle outward",
#             "warehouse|Can download warehouse bundle outward Excel",
#             "warehouse|Can print warehouse current stock",
#             "warehouse|Can download warehouse current stock Excel",
#             "user|Can download user PDF",
#             "user|Can download user Excel",
#             "inquiry|Can print inquiry",
#             "inquiry|Can download inquiry Excel",
#             "inquiry|Can download inquiry PDF",
#             "inquiry|Can add inquiry",
#             "inquiry|Can change inquiry",
#             "inquiry|Can delete inquiry",
#             "inquiry|Can view inquiry",
#             "inquiry|Can add inquiry detail",
#             "inquiry|Can change inquiry detail",
#             "inquiry|Can delete inquiry detail",
#             "inquiry|Can view inquiry detail",
#             "inquiry_quotation|Can add inquiry quotation",
#             "inquiry_quotation|Can change inquiry quotation",
#             "inquiry_quotation|Can delete inquiry quotation",
#             "inquiry_quotation|Can view inquiry quotation",
#             "inquiry_quotation|Can add inquiry quotation detail",
#             "inquiry_quotation|Can change inquiry quotation detail",
#             "inquiry_quotation|Can delete inquiry quotation detail",
#             "inquiry_quotation|Can view inquiry quotation detail",
#             "inquiry_quotation|Can print inquiry quotation",
#             "inquiry_quotation|Can download inquiry quotation Excel",
#             "inquiry_quotation|Can download inquiry quotation PDF",
#             "inquiry_salesorder|Can add inquiry sales order",
#             "inquiry_salesorder|Can change inquiry sales order",
#             "inquiry_salesorder|Can delete inquiry sales order",
#             "inquiry_salesorder|Can view inquiry sales order",
#             "inquiry_salesorder|Can add inquiry salesorder detail",
#             "inquiry_salesorder|Can change inquiry salesorder detail",
#             "inquiry_salesorder|Can delete inquiry salesorder detail",
#             "inquiry_salesorder|Can view inquiry sales order detail",
#             "inquiry_salesorder|Can print Inquiry Sales Order",
#             "inquiry_salesorder|Can download Inquiry Sales Order Excel",
#             "inquiry_salesorder|Can download Inquiry Sales Order PDF",
#         ]

#         design_manager_permissions = [
#             "die|Can add die",
#             "die|Can change die",
#             "die|Can delete die",
#             "die|Can view die",
#             "die|Can add die category",
#             "die|Can change die category",
#             "die|Can delete die category",
#             "die|Can view die category",
#             "die|Can add die group",
#             "die|Can change die group",
#             "die|Can delete die group",
#             "die|Can view die group",
#             "die|Can add die press",
#             "die|Can change die press",
#             "die|Can delete die press",
#             "die|Can view die press",
#             "die|Can add die size",
#             "die|Can change die size",
#             "die|Can delete die size",
#             "die|Can view die size",
#             "die|Can add die sub category",
#             "die|Can change die sub category",
#             "die|Can delete die sub category",
#             "die|Can view die sub category",
#             "die|Can add die tool",
#             "die|Can change die tool",
#             "die|Can delete die tool",
#             "die|Can view die tool",
#             "die|Can add die type",
#             "die|Can change die type",
#             "die|Can delete die type",
#             "die|Can view die type",
#             "user|Can add custom group",
#             "user|Can change custom group",
#             "user|Can delete custom group",
#             "user|Can view custom group",
#             "user|Can add user",
#             "user|Can change user",
#             "user|Can delete user",
#             "user|Can view user",
#             "user|Can add user profile",
#             "user|Can change user profile",
#             "user|Can delete user profile",
#             "user|Can view user profile",
#             "user|Can add auth group model",
#             "user|Can change auth group model",
#             "user|Can delete auth group model",
#             "user|Can view auth group model",
#             "user|Can add auth group permissions model",
#             "user|Can change auth group permissions model",
#             "user|Can delete auth group permissions model",
#             "user|Can view auth group permissions model",
#             "user|Can add auth permission model",
#             "user|Can change auth permission model",
#             "user|Can view auth permission model",
#             "user|Can delete auth permission model",
#             "user|Can add user groups model",
#             "user|Can change user groups model",
#             "user|Can delete user groups model",
#             "user|Can view user groups model",
#             "common|Can view country",
#             "common|Can view currency",
#             "common|Can view financial year model",
#             "common|Can view packing type",
#             "bloster|Can add bloster master",
#             "bloster|Can change bloster master",
#             "bloster|Can delete bloster master",
#             "bloster|Can view bloster master",
#             "vendor|Can add bank details",
#             "vendor|Can change bank details",
#             "vendor|Can delete bank details",
#             "vendor|Can view bank details",
#             "vendor|Can add key persons",
#             "vendor|Can change key persons",
#             "vendor|Can delete key persons",
#             "vendor|Can view key persons",
#             "vendor|Can add vendor",
#             "vendor|Can change vendor",
#             "vendor|Can delete vendor",
#             "vendor|Can view vendor",
#         ]

#         sm_manager_permissions = [
#             "user|Can view auth group model",
#             "user|Can add auth group permissions model",
#             "user|Can change auth group permissions model",
#             "user|Can delete auth group permissions model",
#             "user|Can view auth group permissions model",
#             "user|Can add auth permission model",
#             "user|Can change auth permission model",
#             "user|Can view auth permission model",
#             "user|Can delete auth permission model",
#             "user|Can add user groups model",
#             "user|Can change user groups model",
#             "user|Can delete user groups model",
#             "user|Can view user groups model",
#             "common|Can view country",
#             "common|Can view currency",
#             "common|Can view financial year model",
#             "common|Can view packing type",
#             "workorder|Can add work order",
#             "workorder|Can change work order",
#             "workorder|Can delete work order",
#             "workorder|Can view work order",
#             "workorder|Can add work order detail",
#             "workorder|Can change work order detail",
#             "workorder|Can delete work order detail",
#             "workorder|Can view work order detail",
#             "product|Can add temper",
#             "product|Can change temper",
#             "product|Can delete temper",
#             "product|Can view temper",
#             "quotation|Can add quotation",
#             "quotation|Can change quotation",
#             "quotation|Can delete quotation",
#             "quotation|Can view quotation",
#             "quotation|Can add quotation detail",
#             "quotation|Can change quotation detail",
#             "quotation|Can delete quotation detail",
#             "quotation|Can view quotation detail",
#             "nalco|Can add nalco master",
#             "nalco|Can change nalco master",
#             "nalco|Can delete nalco master",
#             "nalco|Can view nalco master",
#             "product|Can add alloy",
#             "product|Can change alloy",
#             "product|Can delete alloy",
#             "product|Can view alloy",
#             "customer|Can add account group",
#             "customer|Can change account group",
#             "customer|Can delete account group",
#             "customer|Can view account group",
#             "customer|Can add banking details",
#             "customer|Can change banking details",
#             "customer|Can delete banking details",
#             "customer|Can view banking details",
#             "customer|Can add billing person",
#             "customer|Can change billing person",
#             "customer|Can delete billing person",
#             "customer|Can view billing person",
#             "customer|Can add contact person",
#             "customer|Can change contact person",
#             "customer|Can delete contact person",
#             "customer|Can view contact person",
#             "customer|Can add customer",
#             "customer|Can change customer",
#             "customer|Can delete customer",
#             "customer|Can view customer",
#             "customer|Can add customer category",
#             "customer|Can change customer category",
#             "customer|Can delete customer category",
#             "customer|Can view customer category",
#             "customer|Can add customer type",
#             "customer|Can change customer type",
#             "customer|Can delete customer type",
#             "customer|Can view customer type",
#             "customer|Can add site location",
#             "customer|Can change site location",
#             "customer|Can delete site location",
#             "customer|Can view site location",
#             "customer|Can add under group",
#             "customer|Can change under group",
#             "customer|Can delete under group",
#             "customer|Can view under group",
#             "proforma|Can add proforma",
#             "proforma|Can change proforma",
#             "proforma|Can delete proforma",
#             "proforma|Can view proforma",
#             "proforma|Can add proforma details",
#             "proforma|Can change proforma details",
#             "proforma|Can delete proforma details",
#             "proforma|Can view proforma details",
#         ]

#         planning_manager_permissions = [
#             "user|Can view auth group model",
#             "user|Can add auth group permissions model",
#             "user|Can change auth group permissions model",
#             "user|Can delete auth group permissions model",
#             "user|Can view auth group permissions model",
#             "user|Can add auth permission model",
#             "user|Can change auth permission model",
#             "user|Can view auth permission model",
#             "user|Can delete auth permission model",
#             "user|Can add user groups model",
#             "user|Can change user groups model",
#             "user|Can delete user groups model",
#             "user|Can view user groups model",
#             "aging|Can add aging cycle",
#             "aging|Can change aging cycle",
#             "aging|Can delete aging cycle",
#             "aging|Can view aging cycle",
#             "common|Can view country",
#             "common|Can view currency",
#             "common|Can view financial year model",
#             "common|Can view packing type",
#             "die|Can view die",
#             "workorder|Can view work order",
#             "workorder|Can view work order detail",
#         ]

#         dispatch_manager_permission = [
#             "user|Can view auth group model",
#             "user|Can add auth group permissions model",
#             "user|Can change auth group permissions model",
#             "user|Can delete auth group permissions model",
#             "user|Can view auth group permissions model",
#             "user|Can add auth permission model",
#             "user|Can change auth permission model",
#             "user|Can view auth permission model",
#             "user|Can delete auth permission model",
#             "user|Can add user groups model",
#             "user|Can change user groups model",
#             "user|Can delete user groups model",
#             "user|Can view user groups model",
#             "common|Can view country",
#             "common|Can view currency",
#             "common|Can view financial year model",
#             "common|Can view packing type",
#             "bundle_inward|Can add bundle inward",
#             "bundle_inward|Can change bundle inward",
#             "bundle_inward|Can delete bundle inward",
#             "bundle_inward|Can view bundle inward",
#             "bundle_inward|Can add excess stock",
#             "bundle_inward|Can change excess stock",
#             "bundle_inward|Can delete excess stock",
#             "bundle_inward|Can view excess stock",
#             "bundle_outward|Can add bundle outward",
#             "bundle_outward|Can change bundle outward",
#             "bundle_outward|Can delete bundle outward",
#             "bundle_outward|Can view bundle outward",
#             "bundle_outward|Can add bundle outward details",
#             "bundle_outward|Can change bundle outward details",
#             "bundle_outward|Can delete bundle outward details",
#             "bundle_outward|Can view bundle outward details",
#         ]

#         warehouse_manager_group_permission = []

#         self.assign_permissions(super_admin_group, super_admin_permissions)
#         self.assign_permissions(design_manager_group, design_manager_permissions)
#         self.assign_permissions(sm_manager_group, sm_manager_permissions)
#         self.assign_permissions(planning_manager_group, planning_manager_permissions)
#         self.assign_permissions(dispatch_manager_group, dispatch_manager_permission)
#         self.assign_permissions(
#             warehouse_manager_group, warehouse_manager_group_permission
#         )

#     def assign_permissions(self, group, permissions):
#         for permission_name in permissions:
#             try:
#                 app_label, codename = permission_name.split("|")
#                 permission_obj = Permission.objects.get(
#                     content_type__app_label=app_label, name=codename
#                 )
#                 group.permissions.add(permission_obj)
#                 self.stdout.write(
#                     f"Assigned {app_label and codename} permission to {group.name} group"
#                 )
#             except Permission.DoesNotExist:
#                 self.stdout.write(
#                     f"Permission {permission_name} does not exist. Skipping assignment to {group.name} group"
#                 )
#             except Permission.MultipleObjectsReturned:
#                 self.stdout.write(
#                     f"Multiple permissions with the name {permission_name} exist. Skipping assignment to {group.name} group"
#                 )

#     def load_transporter(self):
#         self.stdout.write("Loading Transporter.......")
#         file_path = path.join(
#             settings.BASE_DIR, "core", "management", "source", "transporter.csv"
#         )

#         with open(file_path, "r") as csv_file:
#             reader = csv.DictReader(csv_file, delimiter=",")

#             Transporter.objects.bulk_create(
#                 [
#                     Transporter(
#                         party_name=row["party_name"],
#                         party_code=row["party_code"],
#                         opening_balance=row["opening_balance"],
#                         balance_type=row["balance_type"],
#                         is_cash_amount=row["is_cash_amount"].lower() == "true",
#                         address=row["address"],
#                         city=row["city"],
#                         pincode=row["pincode"],
#                         mobile_no_sms=row["mobile_no_sms"],
#                         mobile_no=row["mobile_no"],
#                         phone_no=row["phone_no"],
#                         email_id=row["email_id"],
#                         send_sms_type=row["send_sms_type"],
#                         is_active=row["is_active"],
#                     )
#                     for row in reader
#                 ],
#                 ignore_conflicts=True,
#             )

#         self.stdout.write("Transporter Data Uploaded SuccessFully.")

#     def load_country(self):
#         self.stdout.write("Loading Country.......")
#         file_path = path.join(
#             settings.BASE_DIR, "core", "management", "source", "country.csv"
#         )

#         with open(file_path, "r") as csv_file:
#             reader = csv.DictReader(csv_file, delimiter=",")

#             Country.objects.bulk_create(
#                 [
#                     Country(
#                         name=row["name"],
#                         code=row["code"],
#                         unicode=row["unicode"],
#                         country_flag=row["flag"],
#                         phone_code=row["phone_code"],
#                     )
#                     for row in reader
#                 ],
#                 ignore_conflicts=True,
#             )
#         self.stdout.write("Country data Uploaded SuccessFully..")

#     def load_die_group(self):
#         self.stdout.write("Loading Die Group...")
#         file_path = path.join(
#             settings.BASE_DIR, "core", "management", "source", "die_group.csv"
#         )
#         created_by_user = User.objects.get(pk=1)

#         with open(file_path, "r") as csv_file:
#             reader = csv.DictReader(csv_file, delimiter=",")
#             for row in reader:
#                 raw_name = row["name"].strip()

#                 if DieGroup.objects.filter(name__iexact=raw_name).exists():
#                     self.stdout.write(
#                         f"Skipped duplicate (case-insensitive): {raw_name}"
#                     )
#                     continue

#                 # Create the DieGroup if not exists
#                 DieGroup.objects.create(
#                     name=raw_name,  # Save original case
#                     deleted=row["deleted"].strip().lower() in ["true", "1"],
#                     created_by=created_by_user,
#                     created_at=datetime.now(),
#                 )
#                 self.stdout.write(f"Created Die Group: {raw_name}")

#         self.stdout.write("Die Group data import complete.")

#     def load_die_category(self):
#         self.stdout.write("Loading Die Category...")
#         file_path = path.join(
#             settings.BASE_DIR, "core", "management", "source", "die_category.csv"
#         )
#         created_by_user = User.objects.get(pk=1)

#         with open(file_path, "r") as csv_file:
#             reader = csv.DictReader(csv_file, delimiter=",")
#             for row in reader:
#                 raw_name = row["name"].strip()

#                 # Case-insensitive check for existing category
#                 if DieCategory.objects.filter(name__iexact=raw_name).exists():
#                     self.stdout.write(
#                         f"kipped duplicate (case-insensitive): {raw_name}"
#                     )
#                     continue

#                 # Create DieCategory
#                 DieCategory.objects.create(
#                     name=raw_name,
#                     deleted=row["deleted"].strip().lower() in ["true", "1"],
#                     created_by=created_by_user,
#                     created_at=datetime.now(),
#                 )
#                 self.stdout.write(f"Created Die Category: {raw_name}")

#         self.stdout.write("Die Category data import complete.")

#     def load_die(self):
#         self.stdout.write("Loading Die data...")
#         file_path = os.path.join(
#             settings.BASE_DIR, "core", "management", "source", "die.csv"
#         )
#         created_by_user = User.objects.get(pk=1)

#         with open(file_path, "r") as csv_file:
#             reader = csv.DictReader(csv_file, delimiter=",")

#             for row in reader:
#                 die_number = row["die_number"].strip()
#                 dimension1 = row["dimension1"].strip()

#                 if die_number == "0":
#                     if Die.objects.filter(
#                         die_number="0", dimension1=dimension1
#                     ).exists():
#                         self.stdout.write(
#                             f"Skipping duplicate die_number=0 and dimension1={dimension1}"
#                         )
#                         continue

#                     Die.objects.create(
#                         die_number=die_number,
#                         dimension1=dimension1,
#                         dimension2=(
#                             Decimal(row["dimension2"]) if row["dimension2"] else None
#                         ),
#                         dimension3=(
#                             Decimal(row["dimension3"]) if row["dimension3"] else None
#                         ),
#                         dimension4=(
#                             Decimal(row["dimension4"]) if row["dimension4"] else None
#                         ),
#                         die_diagram=row["die_diagram"],
#                         wt_kg_p_mt=row["wt_kg_p_mt"],
#                         created_by=created_by_user,
#                         created_at=timezone.now(),
#                     )
#                     self.stdout.write(
#                         f"Die created: die_number=0, dimension1={dimension1}"
#                     )

#                 else:
#                     die, created = Die.objects.get_or_create(
#                         die_number=die_number,
#                         defaults={
#                             "dimension1": dimension1,
#                             "dimension2": (
#                                 Decimal(row["dimension2"])
#                                 if row["dimension2"]
#                                 else None
#                             ),
#                             "dimension3": (
#                                 Decimal(row["dimension3"])
#                                 if row["dimension3"]
#                                 else None
#                             ),
#                             "dimension4": (
#                                 Decimal(row["dimension4"])
#                                 if row["dimension4"]
#                                 else None
#                             ),
#                             "die_diagram": row["die_diagram"],
#                             "wt_kg_p_mt": row["wt_kg_p_mt"],
#                             "created_by": created_by_user,
#                             "created_at": timezone.now(),
#                         },
#                     )
#                     if created:
#                         self.stdout.write(f"Die created: {die_number}")
#                     else:
#                         self.stdout.write(f"Die exists: {die_number}")

#         self.stdout.write("Die data import complete.")

#     def load_currency(self):
#         self.stdout.write("vishwas_automation_private_limited Loading Die data...")
#         file_path = os.path.join(
#             settings.BASE_DIR,
#             "core",
#             "management",
#             "source",
#             "vishwas_automation_private_limited.csv",
#         )
#         created_by_user = User.objects.get(pk=1)

#         with open(file_path, "r") as csv_file:
#             reader = csv.DictReader(csv_file, delimiter=",")

#             for row in reader:
#                 die_number = row["die_number"].strip()
#                 dimension1 = row["dimension1"].strip()

#                 if die_number == "0":
#                     # Check if die with die_number=0 and this dimension1 already exists
#                     if Die.objects.filter(
#                         die_number="0", dimension1=dimension1
#                     ).exists():
#                         self.stdout.write(
#                             f"Skipping duplicate die_number=0 and dimension1={dimension1}"
#                         )
#                         continue

#                     # Create new Die for die_number=0 + unique dimension1
#                     Die.objects.create(
#                         die_number=die_number,
#                         dimension1=dimension1,
#                         dimension2=(
#                             Decimal(row["dimension2"]) if row["dimension2"] else None
#                         ),
#                         dimension3=(
#                             Decimal(row["dimension3"]) if row["dimension3"] else None
#                         ),
#                         dimension4=(
#                             Decimal(row["dimension4"]) if row["dimension4"] else None
#                         ),
#                         die_diagram=row["die_diagram"],
#                         die_group_id=row["die_group"],
#                         die_category_id=row["die_category"],
#                         wt_kg_p_mt=row["wt_kg_p_mt"],
#                         created_by=created_by_user,
#                         created_at=timezone.now(),
#                     )
#                     self.stdout.write(
#                         f"Die created: die_number=0, dimension1={dimension1}"
#                     )

#                 else:
#                     # Normal unique die_number logic
#                     die, created = Die.objects.get_or_create(
#                         die_number=die_number,
#                         defaults={
#                             "dimension1": dimension1,
#                             "dimension2": (
#                                 Decimal(row["dimension2"])
#                                 if row["dimension2"]
#                                 else None
#                             ),
#                             "dimension3": (
#                                 Decimal(row["dimension3"])
#                                 if row["dimension3"]
#                                 else None
#                             ),
#                             "dimension4": (
#                                 Decimal(row["dimension4"])
#                                 if row["dimension4"]
#                                 else None
#                             ),
#                             "die_diagram": row["die_diagram"],
#                             "die_group_id": row["die_group"],
#                             "die_category_id": row["die_category"],
#                             "wt_kg_p_mt": row["wt_kg_p_mt"],
#                             "created_by": created_by_user,
#                             "created_at": timezone.now(),
#                             "approved_at": timezone.now(),
#                         },
#                     )
#                     if created:
#                         self.stdout.write(f"Die created: {die_number}")
#                     else:
#                         self.stdout.write(f"Die exists: {die_number}")

#         self.stdout.write(
#             "vishwas_automation_private_limited Die data import complete."
#         )

#     def _process_row(self, row, created_by_user):
#         """Helper method to process each row of the CSV file."""
#         die_number = row["die_number"].strip()
#         dimension1 = row["dimension1"].strip()

#         if die_number == "0":
#             # Check if die with die_number=0 and this dimension1 already exists
#             if Die.objects.filter(die_number="0", dimension1=dimension1).exists():
#                 self.stdout.write(
#                     f"Skipping duplicate die_number=0 and dimension1={dimension1}"
#                 )
#                 return

#             # Create new Die for die_number=0 + unique dimension1
#             Die.objects.create(
#                 die_number=die_number,
#                 dimension1=dimension1,
#                 dimension2=(Decimal(row["dimension2"]) if row["dimension2"] else None),
#                 dimension3=(Decimal(row["dimension3"]) if row["dimension3"] else None),
#                 dimension4=(Decimal(row["dimension4"]) if row["dimension4"] else None),
#                 die_diagram=row["die_diagram"],
#                 die_group_id=row["die_group"],
#                 die_category_id=row["die_category"],
#                 wt_kg_p_mt=row["wt_kg_p_mt"],
#                 created_by=created_by_user,
#                 created_at=timezone.now(),
#             )
#             self.stdout.write(f"Die created: die_number=0, dimension1={dimension1}")

#         else:
#             # Normal unique die_number logic
#             die, created = Die.objects.get_or_create(
#                 die_number=die_number,
#                 defaults={
#                     "dimension1": dimension1,
#                     "dimension2": (
#                         Decimal(row["dimension2"]) if row["dimension2"] else None
#                     ),
#                     "dimension3": (
#                         Decimal(row["dimension3"]) if row["dimension3"] else None
#                     ),
#                     "dimension4": (
#                         Decimal(row["dimension4"]) if row["dimension4"] else None
#                     ),
#                     "die_diagram": row["die_diagram"],
#                     "die_group_id": row["die_group"],
#                     "die_category_id": row["die_category"],
#                     "wt_kg_p_mt": row["wt_kg_p_mt"],
#                     "created_by": created_by_user,
#                     "created_at": timezone.now(),
#                 },
#             )
#             if created:
#                 self.stdout.write(f"Die created: {die_number}")
#             else:
#                 self.stdout.write(f"Die exists: {die_number}")

#     def load_currency(self):

#         self.stdout.write("Loading Currency.......")
#         file_path = path.join(
#             settings.BASE_DIR, "core", "management", "source", "currency.csv"
#         )

#         try:
#             with open(file_path, "r", encoding="utf-8") as csv_file:
#                 reader = csv.DictReader(csv_file, delimiter=",")

#                 Currency.objects.bulk_create(
#                     [
#                         Currency(
#                             country_id=row["country_id"],
#                             currency_name=row["currency_name"],
#                             currency_code=row["currency_code"],
#                             currency_symbol=row["currency_symbol"],
#                         )
#                         for row in reader
#                     ],
#                     ignore_conflicts=True,
#                 )
#             self.stdout.write("Currency data uploaded.")

#         except UnicodeDecodeError as e:
#             self.stderr.write(f"Error reading the file: {e}")
#             self.stderr.write("Trying with 'latin-1' encoding...")

#             with open(file_path, "r", encoding="latin-1") as csv_file:
#                 reader = csv.DictReader(csv_file, delimiter=",")

#                 Currency.objects.bulk_create(
#                     [
#                         Currency(
#                             country_id=row["country_id"],
#                             currency_name=row["currency_name"],
#                             currency_code=row["currency_code"],
#                             currency_symbol=row["currency_symbol"],
#                         )
#                         for row in reader
#                     ],
#                     ignore_conflicts=True,
#                 )
#             self.stdout.write("Currency data uploaded with 'latin-1' encoding.")

#     def load_financial_data(self):
#         self.stdout.write("Loading Financial Year Data.......")
#         file_path = path.join(
#             settings.BASE_DIR, "core", "management", "source", "financial.csv"
#         )

#         with open(file_path, "r") as csv_file:
#             reader = csv.DictReader(csv_file, delimiter=",")

#             FinancialYearModel.objects.bulk_create(
#                 [
#                     FinancialYearModel(
#                         f_id=0,
#                         financial_year=row["financial_year"],
#                         start_date=row["start_date"],
#                         end_date=row["end_date"],
#                     )
#                     for row in reader
#                 ],
#                 ignore_conflicts=True,
#             )
#         self.stdout.write("Financial data Uploaded SuccessFully..")

#     def load_vehicletype(self):
#         self.stdout.write("Loading VehicleType.......")
#         file_path = path.join(
#             settings.BASE_DIR, "core", "management", "source", "vehicletype.csv"
#         )

#         with open(file_path, "r") as csv_file:
#             reader = csv.DictReader(csv_file, delimiter=",")

#             VehicleType.objects.bulk_create(
#                 [
#                     VehicleType(
#                         vehicle_type=row["vehicle_type"],
#                     )
#                     for row in reader
#                 ],
#                 ignore_conflicts=True,
#             )

#         self.stdout.write("VehicleType Uploaded SuccessFully..")

#     def load_material(self):
#         self.stdout.write("Loading Material.......")
#         file_path = path.join(
#             settings.BASE_DIR, "core", "management", "source", "material.csv"
#         )

#         with open(file_path, "r") as csv_file:
#             reader = csv.DictReader(csv_file, delimiter=",")

#             Material.objects.bulk_create(
#                 [
#                     Material(
#                         material_name=row["material_name"],
#                     )
#                     for row in reader
#                 ],
#                 ignore_conflicts=True,
#             )

#         self.stdout.write("Material Uploaded SuccessFully..")

#     def load_vehiclemaster(self):
#         self.stdout.write("Loading VehicleMaster.......")
#         file_path = path.join(
#             settings.BASE_DIR, "core", "management", "source", "vehicle_master.csv"
#         )

#         with open(file_path, "r") as csv_file:
#             reader = csv.DictReader(csv_file, delimiter=",")

#             VehicleMaster.objects.bulk_create(
#                 [
#                     VehicleMaster(
#                         # Try to link to an existing Transporter; allow None if not found
#                         party_name=Transporter.objects.filter(
#                             party_name=row["party_name"]
#                         ).first(),
#                         vehicle_no=row["vehicle_no"],
#                         tare_wt=row["tare_wt"],
#                     )
#                     for row in reader
#                 ],
#                 ignore_conflicts=True,
#             )
#         self.stdout.write("VehicleMaster Uploaded SuccessFully..")

#     def load_alloy_data(self):
#         self.stdout.write("Loading Alloy Data.......")
#         file_path = path.join(
#             settings.BASE_DIR, "core", "management", "source", "alloy.csv"
#         )

#         with open(file_path, "r") as csv_file:
#             reader = csv.DictReader(csv_file, delimiter=",")
#             Alloy.objects.bulk_create(
#                 [
#                     Alloy(
#                         name=row["name"],
#                         color_code=row["color_code"],
#                         # ingredient=row["ingredient"],
#                         # application=row["application"] or None,
#                         remark=row["remark"] or None,
#                     )
#                     for row in reader
#                 ],
#                 ignore_conflicts=True,
#             )
#         self.stdout.write("Alloy data Uploaded SuccessFully..")

#     def load_temper_data(self):
#         self.stdout.write("Loading Temper Data.......")
#         file_path = path.join(
#             settings.BASE_DIR, "core", "management", "source", "temper.csv"
#         )

#         with open(file_path, "r") as csv_file:
#             reader = csv.DictReader(csv_file, delimiter=",")
#             Temper.objects.bulk_create(
#                 [
#                     Temper(
#                         name=row["name"],
#                     )
#                     for row in reader
#                 ],
#                 ignore_conflicts=True,
#             )
#         self.stdout.write("Temper data Uploaded SuccessFully..")

#     def load_aging_cycle_data(self):
#         self.stdout.write("Loading Aging Cycle Data.......")
#         file_path = path.join(
#             settings.BASE_DIR, "core", "management", "source", "aging_cycle.csv"
#         )

#         # Open the CSV file with the correct encoding
#         with open(file_path, "r", encoding="utf-8") as csv_file:
#             reader = csv.DictReader(csv_file, delimiter=",")
#             AgingCycle.objects.bulk_create(
#                 [
#                     AgingCycle(
#                         alloy=row["alloy"],
#                         temper=row["temper"],
#                         cycle=row["cycle"],
#                         temp=row["temp"],
#                         time=row["time"],
#                         webster=row["webster"],
#                         bhn=row["bhn"],
#                         remark=row["remark"] or None,
#                     )
#                     for row in reader
#                 ],
#                 ignore_conflicts=True,
#             )
#         self.stdout.write("Aging Cycle data Uploaded SuccessFully..")

#     # GST Type Create
#     gst_type_data = [
#         {
#             "id": 1,
#             "name": "sgst",
#             "full_name": "State Goods and Services Tax",
#             "percentage": "9.00",
#             "created_by": 1,
#         },
#         {
#             "id": 2,
#             "name": "cgst",
#             "full_name": "Central Goods and Services Tax",
#             "percentage": "9.00",
#             "created_by": 1,
#         },
#         {
#             "id": 3,
#             "name": "igst",
#             "full_name": "Integrated Goods and Services Tax",
#             "percentage": "18.00",
#             "created_by": 1,
#         },
#         {
#             "id": 4,
#             "name": "utgst",
#             "full_name": "Union Territory Goods and Services Tax",
#             "percentage": "9.00",
#             "created_by": 1,
#         },
#     ]

#     def load_gst_type_data(self):
#         self.stdout.write("Loading GST Type Data...........")
#         created_by_user = User.objects.get(pk=1)
#         gst_types = []

#         for data in self.gst_type_data:
#             gst_type, created = GstType.objects.update_or_create(
#                 id=data["id"],  # Use id to update or create
#                 defaults={
#                     "name": data["name"],
#                     "full_name": data["full_name"],
#                     "percentage": data["percentage"],
#                     "created_by": created_by_user,
#                     "updated_by": created_by_user,
#                 },
#             )
#             gst_types.append(gst_type)

#         self.stdout.write("GST Type data Uploaded SuccessFully..")
#         return gst_types

#     def load_section_type(self):
#         """Load Section Type data from CSV file"""
#         self.stdout.write("Loading Section Type Data.......")
#         file_path = path.join(
#             settings.BASE_DIR, "core", "management", "source", "section_type.csv"
#         )

#         try:
#             created_by_user = User.objects.get(pk=1)
#         except User.DoesNotExist:
#             self.stdout.write(
#                 "Warning: User with pk=1 not found. Creating section types without created_by."
#             )
#             created_by_user = None

#         with open(file_path, "r", encoding="utf-8") as csv_file:
#             reader = csv.DictReader(csv_file, delimiter=",")

#             section_types = []
#             for row in reader:
#                 name = row["name"].strip()

#                 # Case-insensitive check for existing section type
#                 if SectionType.objects.filter(
#                     name__iexact=name, is_archived=False
#                 ).exists():
#                     self.stdout.write(f"Skipped duplicate (case-insensitive): {name}")
#                     continue

#                 # Create SectionType
#                 section_type = SectionType(
#                     name=name,
#                     is_active=True,
#                     is_archived=False,
#                     created_by=created_by_user,
#                     updated_by=created_by_user,
#                 )
#                 section_types.append(section_type)
#                 self.stdout.write(f"Created Section Type: {name}")

#             # Bulk create all section types
#             if section_types:
#                 SectionType.objects.bulk_create(section_types, ignore_conflicts=True)
#                 self.stdout.write(
#                     f"Section Type data uploaded successfully. Created {len(section_types)} section types."
#                 )
#             else:
#                 self.stdout.write("No new section types to create.")

#         self.stdout.write("Section Type data Uploaded SuccessFully..")

#     def load_department(self):
#         """Load Department data from CSV file"""
#         self.stdout.write("Loading Department Data.......")
#         file_path = path.join(
#             settings.BASE_DIR, "core", "management", "source", "department.csv"
#         )

#         try:
#             created_by_user = User.objects.get(pk=1)
#         except User.DoesNotExist:
#             self.stdout.write(
#                 "Warning: User with pk=1 not found. Creating departments without created_by."
#             )
#             created_by_user = None

#         with open(file_path, "r", encoding="utf-8") as csv_file:
#             reader = csv.DictReader(csv_file, delimiter=",")

#             departments = []
#             for row in reader:
#                 department_code = row["department_code"].strip().upper()
#                 department_name = row["department_name"].strip()

#                 # Case-insensitive check for existing department code
#                 if Department.objects.filter(
#                     department_code__iexact=department_code, is_archived=False
#                 ).exists():
#                     self.stdout.write(
#                         f"Skipped duplicate (case-insensitive): {department_code}"
#                     )
#                     continue

#                 # Get plant by name (required)
#                 plant_name = row.get("plant_name", "").strip()
#                 if not plant_name:
#                     self.stdout.write(
#                         f"Error: Plant Name is required. Skipping department '{department_code}'."
#                     )
#                     continue

#                 try:
#                     plant = Plant.objects.filter(
#                         plant_name__iexact=plant_name, deleted=False
#                     ).first()
#                     if not plant:
#                         self.stdout.write(
#                             f"Error: Plant '{plant_name}' not found. Skipping department '{department_code}'."
#                         )
#                         continue
#                 except Exception as e:
#                     self.stdout.write(
#                         f"Error looking up plant '{plant_name}': {str(e)}. Skipping department '{department_code}'."
#                     )
#                     continue

#                 # Get parent department if provided
#                 parent_department = None
#                 parent_code = row.get("parent_department_code", "").strip()
#                 if parent_code:
#                     try:
#                         # Look for parent in same plant (plant is required)
#                         parent_department = Department.objects.filter(
#                             department_code__iexact=parent_code.upper(),
#                             plant=plant,
#                             is_archived=False,
#                         ).first()

#                         if not parent_department:
#                             self.stdout.write(
#                                 f"Warning: Parent department '{parent_code}' not found in plant '{plant.plant_name}' for department '{department_code}'"
#                             )
#                     except Exception as e:
#                         self.stdout.write(
#                             f"Error looking up parent department '{parent_code}': {str(e)}"
#                         )

#                 # Create Department
#                 department = Department(
#                     department_code=department_code,
#                     department_name=department_name,
#                     department_type=row.get("department_type", "PRODUCTION")
#                     .strip()
#                     .upper(),
#                     plant=plant,
#                     cost_center_code=row.get("cost_center_code", "").strip() or None,
#                     parent_department=parent_department,
#                     status=row.get("status", "Active").strip(),
#                     is_archived=False,
#                     created_by=created_by_user,
#                     updated_by=created_by_user,
#                 )
#                 departments.append(department)
#                 self.stdout.write(
#                     f"Created Department: {department_code} - {department_name}"
#                 )

#             # Bulk create all departments
#             if departments:
#                 Department.objects.bulk_create(departments, ignore_conflicts=True)
#                 self.stdout.write(
#                     f"Department data uploaded successfully. Created {len(departments)} departments."
#                 )
#             else:
#                 self.stdout.write("No new departments to create.")

#         self.stdout.write("Department data Uploaded SuccessFully..")

#     def load_item_category(self):
#         """Load Item Category data from CSV file"""
#         self.stdout.write("Loading Item Category Data.......")
#         file_path = path.join(
#             settings.BASE_DIR, "core", "management", "source", "item_category.csv"
#         )

#         try:
#             created_by_user = User.objects.get(pk=1)
#         except User.DoesNotExist:
#             self.stdout.write(
#                 "Warning: User with pk=1 not found. Creating item categories without created_by."
#             )
#             created_by_user = None

#         with open(file_path, "r", encoding="utf-8") as csv_file:
#             reader = csv.DictReader(csv_file, delimiter=",")

#             item_categories = []
#             for row in reader:
#                 category_code = row["category_code"].strip().upper()
#                 category_name = row["category_name"].strip()

#                 # Case-insensitive check for existing category code
#                 if ItemCategory.objects.filter(
#                     category_code__iexact=category_code, is_archived=False
#                 ).exists():
#                     self.stdout.write(
#                         f"Skipped duplicate (case-insensitive): {category_code}"
#                     )
#                     continue

#                 # Create ItemCategory
#                 item_category = ItemCategory(
#                     category_code=category_code,
#                     category_name=category_name,
#                     allowed_item_type=row.get("allowed_item_type", "RAW")
#                     .strip()
#                     .upper(),
#                     description=row.get("description", "").strip() or None,
#                     is_active=row.get("is_active", "True").strip().lower() == "true",
#                     is_archived=False,
#                     created_by=created_by_user,
#                     updated_by=created_by_user,
#                 )
#                 item_categories.append(item_category)
#                 self.stdout.write(
#                     f"Created Item Category: {category_code} - {category_name}"
#                 )

#             # Bulk create all item categories
#             if item_categories:
#                 ItemCategory.objects.bulk_create(item_categories, ignore_conflicts=True)
#                 self.stdout.write(
#                     f"Item Category data uploaded successfully. Created {len(item_categories)} item categories."
#                 )
#             else:
#                 self.stdout.write("No new item categories to create.")

#         self.stdout.write("Item Category data Uploaded SuccessFully..")

#     def load_yield_unit(self):
#         """Load YieldUnit data"""
#         self.stdout.write("Loading YieldUnit Data.......")

#         try:
#             created_by_user = User.objects.get(pk=1)
#         except User.DoesNotExist:
#             self.stdout.write(
#                 "Warning: User with pk=1 not found. Creating yield units without created_by."
#             )
#             created_by_user = None

#         yield_unit_names = ["MPa", "N/mm", "ksi"]
#         yield_units = []

#         for name in yield_unit_names:
#             # Check if yield unit already exists (case-insensitive)
#             if YieldUnit.objects.filter(name__iexact=name, deleted=False).exists():
#                 self.stdout.write(f"Skipped duplicate (case-insensitive): {name}")
#                 continue

#             yield_unit = YieldUnit(
#                 name=name,
#                 deleted=False,
#                 created_by=created_by_user,
#                 updated_by=created_by_user,
#             )
#             yield_units.append(yield_unit)
#             self.stdout.write(f"Created YieldUnit: {name}")

#         # Bulk create all yield units
#         if yield_units:
#             YieldUnit.objects.bulk_create(yield_units, ignore_conflicts=True)
#             self.stdout.write(
#                 f"YieldUnit data uploaded successfully. Created {len(yield_units)} yield units."
#             )
#         else:
#             self.stdout.write("No new yield units to create.")

#         self.stdout.write("YieldUnit data Uploaded SuccessFully..")
