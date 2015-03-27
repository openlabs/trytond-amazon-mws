# -*- coding: utf-8 -*-
"""
    __init__

    Initialize module

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool
from .channel import (
    SaleChannel, CheckServiceStatus, CheckServiceStatusView,
    CheckAmazonSettingsView, CheckAmazonSettings
)
from .product import (
    Product, ExportCatalogStart, ExportCatalog,
    ExportCatalogDone, ExportCatalogPricingStart, ExportCatalogPricing,
    ExportCatalogPricingDone, ExportCatalogInventoryStart,
    ExportCatalogInventory, ExportCatalogInventoryDone, ProductCode, Template,
)


def register():
    """
    Register classes with pool
    """
    Pool.register(
        SaleChannel,
        Product,
        ProductCode,
        Template,
        ExportCatalogStart,
        ExportCatalogDone,
        ExportCatalogPricingStart,
        ExportCatalogPricingDone,
        ExportCatalogInventoryStart,
        ExportCatalogInventoryDone,
        CheckServiceStatusView,
        CheckAmazonSettingsView,
        module='amazon_mws', type_='model'
    )
    Pool.register(
        CheckServiceStatus,
        CheckAmazonSettings,
        ExportCatalog,
        ExportCatalogPricing,
        ExportCatalogInventory,
        module='amazon_mws', type_='wizard'
    )
