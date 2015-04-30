# -*- coding: utf-8 -*-
"""
    __init__

    Initialize module

    :copyright: (c) 2013-2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool
from channel import (
    SaleChannel, CheckAmazonServiceStatus, CheckAmazonServiceStatusView,
    CheckAmazonSettingsView, CheckAmazonSettings, ImportAmazonOrdersView,
    ImportAmazonOrders
)
from product import (
    Product, ExportAmazonCatalogStart, ExportAmazonCatalog,
    ExportAmazonCatalogDone, ExportAmazonPricingStart, ExportAmazonPricing,
    ExportAmazonPricingDone, ExportAmazonInventoryStart,
    ExportAmazonInventory, ExportAmazonInventoryDone, ProductCode, Template
)
from sale import Sale
from party import Party, Address
from country import Subdivision


def register():
    """
    Register classes with pool
    """
    Pool.register(
        SaleChannel,
        Product,
        ProductCode,
        Template,
        ExportAmazonCatalogStart,
        ExportAmazonCatalogDone,
        ExportAmazonPricingStart,
        ExportAmazonPricingDone,
        ExportAmazonInventoryStart,
        ExportAmazonInventoryDone,
        CheckAmazonServiceStatusView,
        CheckAmazonSettingsView,
        ImportAmazonOrdersView,
        Sale,
        Party,
        Address,
        Subdivision,
        module='amazon_mws', type_='model'
    )
    Pool.register(
        CheckAmazonServiceStatus,
        CheckAmazonSettings,
        ExportAmazonCatalog,
        ExportAmazonPricing,
        ExportAmazonInventory,
        ImportAmazonOrders,
        module='amazon_mws', type_='wizard'
    )
