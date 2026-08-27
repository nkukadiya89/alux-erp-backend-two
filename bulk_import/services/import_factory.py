from .alloy_importer import AlloyImporter
from .blosters_importer import BlostersImporter
from .conversionrate_importer import ConversionRateImporter
from .customer_importer import CustomerImporter
from .customer_type_importer import CustomerTypeImporter
from .nalco_importer import NalcoImporter
from .packingmode_importer import PackingModeImporter
from .sectioncategory_importer import SectionCategoryImporter
from .sectiongroup_importer import SectionGroupImporter
from .sectionpress_importer import SectionPressImporter
from .sectionsize_importer import SectionSizeImporter
from .sectionsubcategory_importer import SectionSubCategoryImporter
from .temper_importer import TemperImporter
from .vendor_importer import VendorImporter


class ImportFactory:
    """Factory to get appropriate importer based on type"""

    IMPORTERS = {
        "customer": CustomerImporter,
        "customer_type": CustomerTypeImporter,
        "customertype": CustomerTypeImporter,
        "bloster": BlostersImporter,
        "bolster": BlostersImporter,
        "alloy": AlloyImporter,
        "temper": TemperImporter,
        "conversionrate": ConversionRateImporter,
        "packingmode": PackingModeImporter,
        "sectionpress": SectionPressImporter,
        "sectionsize": SectionSizeImporter,
        "vendor": VendorImporter,
        "sectiongroup": SectionGroupImporter,
        "sectioncategory": SectionCategoryImporter,
        "sectionsubcategory": SectionSubCategoryImporter,
        "nalco": NalcoImporter,
    }

    @classmethod
    def get_importer(cls, master_type: str, import_job_id: int):
        """Get importer instance for given type"""
        if master_type not in cls.IMPORTERS:
            raise ValueError(f"Unsupported import type: {master_type}")

        importer_class = cls.IMPORTERS[master_type]
        return importer_class(import_job_id)

    @classmethod
    def get_supported_types(cls):
        """Get list of supported import types"""
        return list(cls.IMPORTERS.keys())
