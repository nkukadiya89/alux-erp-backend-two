from django.contrib.auth.models import Permission

from user.models import AuthGroupPermissionsModel, AuthPermissionModel, CustomGroup
from vendor.models import Vendor


def get_permission_by_group_ids(
    group_ids, user_assigned_groups=None, user_assgined_permissions=None
):
    permission_dict = {}

    # Fetch all permissions for the assigned user groups
    all_default_permissions = AuthGroupPermissionsModel.objects.filter(
        group__name=user_assigned_groups
    )

    for default_permission in all_default_permissions:
        permission = Permission.objects.get(id=default_permission.permission.id)
        permission_detail = {
            "id": None,
            "permission_id": permission.id,
            "name": default_permission.permission.name,
            "codename": permission.codename,
            "content_type_id": default_permission.permission.content_type.id,
            "model_name": default_permission.permission.content_type.app_label.capitalize(),
            "is_checked": False,
        }
        permission_dict[permission.id] = permission_detail

    # Fetch From Given Group ID
    group_ids_permissions = AuthGroupPermissionsModel.objects.filter(
        group_id__in=group_ids
    )
    for group_permission in group_ids_permissions:
        permission = Permission.objects.get(id=group_permission.permission.id)
        permission_detail = {
            "id": group_permission.id,
            "permission_id": permission.id,
            "name": group_permission.permission.name,
            "codename": permission.codename,
            "content_type_id": group_permission.permission.content_type.id,
            "model_name": group_permission.permission.content_type.app_label.capitalize(),
            "is_checked": True,
        }
        permission_dict[permission.id] = permission_detail

    # Fetch From Given Employee ID
    if user_assgined_permissions:
        user_assigned_permission_ids = user_assgined_permissions.values_list(
            "id", flat=True
        )
        user_assigned_permission = Permission.objects.filter(
            id__in=user_assigned_permission_ids
        )
        for user_permission in user_assigned_permission:
            permission_detail = {
                "id": None,
                "permission_id": user_permission.id,
                "name": user_permission.name,
                "codename": user_permission.codename,
                "content_type_id": user_permission.content_type.id,
                "model_name": user_permission.content_type.app_label.capitalize(),
                "is_checked": True,
            }
            permission_dict[user_permission.id] = permission_detail

    response = list(permission_dict.values())

    return response


def get_purticlare_permission(
    content_types, model_names, group_id, company_id, vendor_id
):
    get_all_groups = None
    if company_id:
        try:
            company_instance = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return {"Company Not Found"}

        get_groups = CustomGroup.objects.filter(
            name__icontains="Company Admin"
        ).values_list("name", flat=True)
        get_company_groups = CustomGroup.objects.filter(
            company=company_instance
        ).values_list("name", flat=True)
        get_all_groups = list(get_groups) + list(get_company_groups)

    elif vendor_id:
        try:
            vendor_instance = Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            return {"Vendor Not Found"}

        get_groups = CustomGroup.objects.filter(
            name__icontains="Vendor Admin"
        ).values_list("name", flat=True)
        get_vendor_groups = CustomGroup.objects.filter(
            vendor=vendor_instance
        ).values_list("name", flat=True)
        get_all_groups = list(get_groups) + list(get_vendor_groups)

    else:
        get_super_admin_groups = CustomGroup.objects.filter(
            name__icontains="Super Admin"
        )
        get_all_groups = list(get_super_admin_groups.values_list("name", flat=True))

    permission_list = []

    group_permissions = AuthGroupPermissionsModel.objects.filter(
        permission__content_type=content_types,
        permission__content_type__model=model_names,
        group__name__in=get_all_groups,
    )
    permissions_qs = Permission.objects.filter(
        id__in=group_permissions.values_list("permission__id", flat=True)
    )

    permission_by_groups = []
    if group_id:
        permission_by_group = AuthGroupPermissionsModel.objects.filter(
            group_id=group_id,
            permission__content_type__id=content_types,
            permission__content_type__model=model_names,
        )
        for permission_group in permission_by_group:
            group_by_permission = {
                "name": permission_group.permission.name,
                "content_type_id": permission_group.permission.content_type.id,
                "is_checked": True,
            }
            permission_by_groups.append(group_by_permission)

    for grp_permission in permissions_qs:
        permission_detail = {
            "id": grp_permission.id,
            "name": grp_permission.name,
            "codename": "codename",
            "content_type_id": grp_permission.content_type.id,
            "model_name": grp_permission.content_type.app_label.capitalize(),
            "is_checked": False,
        }
        permission_list.append(permission_detail)

    if len(permission_by_groups) > 0:
        for permission_by_group in permission_by_groups:
            for permission in permission_list:
                if (
                    permission["name"] == permission_by_group["name"]
                    and permission["content_type_id"]
                    == permission_by_group["content_type_id"]
                ):
                    permission["is_checked"] = True

    return permission_list


def get_group_permission_by_user(custom_group, exclude_group):
    user_group_permissions = {}
    exclude_group_ids = [group.id for group in exclude_group]

    for group in custom_group:
        custom_group_name = group.group_name
        group_id = group.id

        group_role_family = group.role_family.family_name if group.role_family else None

        if custom_group_name not in user_group_permissions:
            user_group_permissions[custom_group_name] = {
                "group_id": group_id,
                "group_role_family": group_role_family,
                "group_name": custom_group_name,
                "permissions": [],
            }

        permission_by_group = AuthPermissionModel.objects.filter(
            authgrouppermissionsmodel__group_id=group_id
        )

        permissions_not_in_group = AuthPermissionModel.objects.filter(
            authgrouppermissionsmodel__group_id__in=exclude_group_ids
        ).exclude(id__in=permission_by_group.values_list("id", flat=True))

        for permission_group in permission_by_group:
            group_permission = AuthGroupPermissionsModel.objects.get(
                permission=permission_group, group_id=group_id
            )

            permission_entry = {
                "id": group_permission.id,
                "permission_id": permission_group.id,
                "name": permission_group.name,
                "model_name": permission_group.content_type.app_label.capitalize(),
                "is_checked": True,
            }
            user_group_permissions[custom_group_name]["permissions"].append(
                permission_entry
            )

        for permission in permissions_not_in_group:
            permission_entry = {
                "id": None,
                "permission_id": permission.id,
                "name": permission.name,
                "model_name": permission.content_type.app_label.capitalize(),
                "is_checked": False,
            }
            user_group_permissions[custom_group_name]["permissions"].append(
                permission_entry
            )

    response = list(user_group_permissions.values())
    return {"user_group_permissions": response}


def create_role_family(request, company_id):
    company_group = []
    cxo_family_permissions = [
        "purchase_requisition|Can view purchase requisition master",
        "purchase_requisition|Can view purchase requisition details",
        "purchase_requisition|Can view purchase requisition site",
        "purchase_requisition|Can view purchase requisition approval",
    ]

    buyer_family_permissions = [
        "rfq|Can add float rfq",
        "rfq|Can change float rfq",
        "rfq|Can delete float rfq",
        "rfq|Can view float rfq",
        "rfq|Can add rfq",
        "rfq|Can change rfq",
        "rfq|Can delete rfq",
        "rfq|Can view rfq",
        "rfq|Can add rfq material detail",
        "rfq|Can change rfq material detail",
        "rfq|Can delete rfq material detail",
        "rfq|Can view rfq material detail",
        "rfq|Can add rfq vendor detail",
        "rfq|Can change rfq vendor detail",
        "rfq|Can delete rfq vendor detail",
        "rfq|Can view rfq vendor detail",
        "rfq|Can add po order",
        "rfq|Can change po order",
        "rfq|Can delete po order",
        "rfq|Can view po order",
        "purchase_requisition|Can view purchase requisition master",
        "purchase_requisition|Can view purchase requisition details",
        "purchase_requisition|Can view purchase requisition site",
        "purchase_requisition|Can view purchase requisition approval",
    ]

    project_eng_plan_family_permissions = [
        "purchase_requisition|Can add purchase requisition master",
        "purchase_requisition|Can change purchase requisition master",
        "purchase_requisition|Can delete purchase requisition master",
        "purchase_requisition|Can view purchase requisition master",
        "purchase_requisition|Can add purchase requisition details",
        "purchase_requisition|Can change purchase requisition details",
        "purchase_requisition|Can delete purchase requisition details",
        "purchase_requisition|Can view purchase requisition details",
        "purchase_requisition|Can add purchase requisition site",
        "purchase_requisition|Can change purchase requisition site",
        "purchase_requisition|Can delete purchase requisition site",
        "purchase_requisition|Can view purchase requisition site",
        "purchase_requisition|Can add purchase requisition approval",
        "purchase_requisition|Can change purchase requisition approval",
        "purchase_requisition|Can delete purchase requisition approval",
        "purchase_requisition|Can view purchase requisition approval",
    ]

    role_data = [
        # Buyer Family
        {
            "name": f"company_{company_id}_Buyer",
            "group_name": "Buyer",
            "company_id": company_id,
            "role_family": 1,
            "permissions": buyer_family_permissions,
        },
        {
            "name": f"company_{company_id}_Senior_Buyer",
            "group_name": "Senior Buyer",
            "company_id": company_id,
            "role_family": 1,
            "permissions": buyer_family_permissions,
        },
        {
            "name": f"company_{company_id}_Procurment_Lead",
            "group_name": "Procurment Lead",
            "company_id": company_id,
            "role_family": 1,
            "permissions": buyer_family_permissions,
        },
        {
            "name": f"company_{company_id}_Procurment_Head",
            "group_name": "Procurment Head",
            "company_id": company_id,
            "role_family": 1,
            "permissions": buyer_family_permissions,
        },
        {
            "name": f"company_{company_id}_Chief Procurement_Officer_(CPO)",
            "group_name": "Chief Procurement Officer (CPO)",
            "company_id": company_id,
            "role_family": 1,
            "permissions": buyer_family_permissions,
        },
        # CXO Family
        {
            "name": f"company_{company_id}_Chief_Finance_Officer_(CFO)",
            "group_name": "Chief Finance Officer (CFO)",
            "company_id": company_id,
            "role_family": 2,
            "permissions": cxo_family_permissions,
        },
        {
            "name": f"company_{company_id}_Chief_Executive_Officer_(CEO)",
            "group_name": "Chief Executive Officer (CEO)",
            "company_id": company_id,
            "role_family": 2,
            "permissions": cxo_family_permissions,
        },
        # Finanace Family
        {
            "name": f"company_{company_id}_Finance_Controller_(FC)",
            "group_name": "Finance Controller (FC)",
            "company_id": company_id,
            "role_family": 3,
            "permissions": cxo_family_permissions,
        },
        # Project Family
        {
            "name": f"company_{company_id}_Purchase_Requisitioner_(PR creator)",
            "group_name": "Purchase Requisitioner (PR creator)",
            "company_id": company_id,
            "role_family": 4,
            "permissions": project_eng_plan_family_permissions,
        },
        {
            "name": f"company_{company_id}_Site_Incharge",
            "group_name": "Site Incharge",
            "company_id": company_id,
            "role_family": 4,
            "permissions": project_eng_plan_family_permissions,
        },
        {
            "name": f"company_{company_id}_Project_Manager",
            "group_name": "Project Manager",
            "company_id": company_id,
            "role_family": 4,
            "permissions": project_eng_plan_family_permissions,
        },
        {
            "name": f"company_{company_id}_Project_Director",
            "group_name": "Project Director",
            "company_id": company_id,
            "role_family": 4,
            "permissions": project_eng_plan_family_permissions,
        },
        {
            "name": f"company_{company_id}_Direct_of_Project(s)",
            "group_name": "Direct of Project(s)",
            "company_id": company_id,
            "role_family": 4,
            "permissions": project_eng_plan_family_permissions,
        },
        # Eng. Family
        {
            "name": f"company_{company_id}_Engineering_Incharge",
            "group_name": "Engineering Incharge",
            "company_id": company_id,
            "role_family": 5,
            "permissions": project_eng_plan_family_permissions,
        },
        {
            "name": f"company_{company_id}_Engineering_Head",
            "group_name": "Engineering Head",
            "company_id": company_id,
            "role_family": 5,
            "permissions": project_eng_plan_family_permissions,
        },
        # Planning Family
        {
            "name": f"company_{company_id}_Planning_Incharge_(Cost and schedule Controller)",
            "group_name": "Planning Incharge (Cost and schedule Controller)",
            "company_id": company_id,
            "role_family": 6,
            "permissions": project_eng_plan_family_permissions,
        },
        {
            "name": f"company_{company_id}_Planning_Head",
            "group_name": "Planning Head",
            "company_id": company_id,
            "role_family": 6,
            "permissions": project_eng_plan_family_permissions,
        },
    ]

    for data in role_data:
        try:
            role_family_instance = RoleFamily.objects.get(id=data["role_family"])
        except RoleFamily.DoesNotExist:
            return {"success": False, "message": "Family Not Found"}

        try:
            company_instance = Company.objects.get(id=data["company_id"])
        except Company.DoesNotExist:
            return {"success": False, "message": "Company Not Found"}

        try:
            company_wise_group = CustomGroup.objects.create(
                name=data["name"],
                group_name=data["group_name"],
                company=company_instance,
                role_family=role_family_instance,
            )

            for permission in data["permissions"]:
                app_label, codename = permission.split("|")
                try:
                    permission_obj = Permission.objects.get(
                        content_type__app_label=app_label, name=codename
                    )
                    company_wise_group.permissions.add(permission_obj)
                except Permission.DoesNotExist:
                    return {
                        "success": False,
                        "message": f"Permission '{codename}' not found for app '{app_label}'",
                    }

            company_group.append(company_wise_group)
        except Exception as e:
            return {"success": False, "message": str(e)}

    return {"success": True, "company_group": company_group}


def create_vendor_role(vendor_id):
    vendor_group = []
    sales_manager = [
        "rfq|Can view float rfq",
        "rfq|Can view rfq",
        "rfq|Can view rfq material detail",
        "rfq|Can view rfq vendor detail",
        "rfq|Can add rfq vendor assign sales manager",
        "rfq|Can change rfq vendor assign sales manager",
        "rfq|Can delete rfq vendor assign sales manager",
        "rfq|Can view rfq vendor assign sales manager",
        "rfq|Can add bid rfq",
        "rfq|Can change bid rfq",
        "rfq|Can delete bid rfq",
        "rfq|Can view bid rfq",
    ]

    role_data = [
        {
            "name": f"vendor_{vendor_id}_SalesManager",
            "group_name": "Sales Manager",
            "vendor_id": vendor_id,
            "permissions": sales_manager,
        }
    ]
    for data in role_data:
        try:
            vendor_instance = Vendor.objects.get(id=data["vendor_id"])
        except Vendor.DoesNotExist:
            return {"success": False, "message": "Vendor Not Found"}
        try:
            company_wise_group = CustomGroup.objects.create(
                name=data["name"],
                group_name=data["group_name"],
                vendor=vendor_instance,
            )

            for permission in data["permissions"]:
                app_label, codename = permission.split("|")
                try:
                    permission_obj = Permission.objects.get(
                        content_type__app_label=app_label, name=codename
                    )
                    company_wise_group.permissions.add(permission_obj)
                except Permission.DoesNotExist:
                    return {
                        "success": False,
                        "message": f"Permission '{codename}' not found for app '{app_label}'",
                    }

            vendor_group.append(company_wise_group)
        except Exception as e:
            return {"success": False, "message": str(e)}

    return {"success": True, "vendor_group": vendor_group}
    return {"success": True, "vendor_group": vendor_group}
    return {"success": True, "vendor_group": vendor_group}
