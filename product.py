# -*- coding: UTF-8 -*-
'''
    product

    :copyright: (c) 2013-2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
'''
from decimal import Decimal

from trytond.model import ModelView, fields
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import PoolMeta, Pool


__all__ = [
    'Product', 'ExportAmazonCatalogStart', 'ExportAmazonCatalog',
    'ExportAmazonCatalogDone', 'ExportAmazonPricingStart',
    'ExportAmazonPricing', 'ExportAmazonPricingDone',
    'ExportAmazonInventoryStart', 'ExportAmazonInventory',
    'ExportAmazonInventoryDone', 'ProductCode',
    'Template',
]
__metaclass__ = PoolMeta


class Template:
    "Product Template"
    __name__ = 'product.template'

    export_to_amazon = fields.Boolean('Amazon Exportable')


class Product:
    "Product"
    __name__ = "product.product"

    asin = fields.Function(fields.Many2One(
        'product.product.code', 'ASIN'
    ), 'get_codes')
    ean = fields.Function(fields.Many2One(
        'product.product.code', 'EAN'
    ), 'get_codes')
    upc = fields.Function(fields.Many2One(
        'product.product.code', 'UPC'
    ), 'get_codes')
    isbn = fields.Function(fields.Many2One(
        'product.product.code', 'ISBN'
    ), 'get_codes')
    gtin = fields.Function(fields.Many2One(
        'product.product.code', 'GTIN'
    ), 'get_codes')

    @classmethod
    def get_codes(cls, products, names):
        ProductCode = Pool().get('product.product.code')

        res = {}
        for name in names:
            res[name] = {}
            for product in products:
                code = ProductCode.search([
                    ('product', '=', product.id),
                    ('code_type', '=', name)
                ])
                res[name][product.id] = code and code[0].id or None

        return res

    @classmethod
    def find_or_create_using_amazon_sku(cls, sku):
        """
        Find or create a product using Amazon Seller SKU. This method looks
        for an existing product using the SKU provided. If found, it
        returns the product found, else creates a new one and returns that

        :param sku: Product Seller SKU from Amazon
        :returns: Active record of Product Created
        """
        SaleChannel = Pool().get('sale.channel')

        products = cls.search([('code', '=', sku)])

        if products:
            return products[0]

        # if product is not found get the info from amazon and
        # delegate to create_using_amazon_data
        amazon_channel = SaleChannel(
            Transaction().context['current_channel']
        )
        assert amazon_channel.source == 'amazon_mws'

        api = amazon_channel.get_amazon_product_api()

        product_data = api.get_matching_product_for_id(
            amazon_channel.amazon_marketplace_id, 'SellerSKU', [sku]
        ).parsed

        return cls.create_using_amazon_data(product_data)

    @classmethod
    def extract_product_values_from_amazon_data(cls, product_attributes):
        """
        Extract product values from the amazon data, used for
        creation of product. This method can be overwritten by
        custom modules to store extra info to a product

        :param product_data: Product data from amazon
        :returns: Dictionary of values
        """
        SaleChannel = Pool().get('sale.channel')

        amazon_channel = SaleChannel(
            Transaction().context['current_channel']
        )
        assert amazon_channel.source == 'amazon_mws'

        return {
            'name': product_attributes['Title']['value'],
            'list_price': Decimal('0.01'),
            'cost_price': Decimal('0.01'),
            'default_uom': amazon_channel.default_uom.id,
            'salable': True,
            'sale_uom': amazon_channel.default_uom.id,
            'account_expense': amazon_channel.default_account_expense.id,
            'account_revenue': amazon_channel.default_account_revenue.id,
        }

    @classmethod
    def create_using_amazon_data(cls, product_data):
        """
        Create a new product with the `product_data` from amazon.

        :param product_data: Product Data from Amazon
        :returns: Active record of product created
        """
        Template = Pool().get('product.template')

        # TODO: Handle attribute sets in multiple languages
        product_attribute_set = product_data['Products']['Product'][
            'AttributeSets'
        ]
        if isinstance(product_attribute_set, dict):
            product_attributes = product_attribute_set['ItemAttributes']
        else:
            product_attributes = product_attribute_set[0]['ItemAttributes']

        product_values = cls.extract_product_values_from_amazon_data(
            product_attributes
        )

        product_values.update({
            'products': [('create', [{
                'code': product_data['Id']['value'],
                'description': product_attributes['Title']['value'],
                'channel_listings': [('create', [{
                    # TODO: Set product identifier
                    'channel': Transaction().context['current_channel']
                }])]
            }])],
        })

        product_template, = Template.create([product_values])

        return product_template.products[0]


class ProductCode:
    "Amazon Product Identifier"
    __name__ = 'product.product.code'

    @classmethod
    def __setup__(cls):
        """
        Setup the class before adding to pool
        """
        super(ProductCode, cls).__setup__()
        cls.code_type.selection.extend([
            ('upc', 'UPC'),
            ('isbn', 'ISBN'),
            ('asin', 'ASIN'),
            ('gtin', 'GTIN')
        ])


class ExportAmazonCatalogStart(ModelView):
    'Export Catalog to Amazon View'
    __name__ = 'amazon.export_catalog.start'


class ExportAmazonCatalogDone(ModelView):
    'Export Catalog to Amazon Done View'
    __name__ = 'amazon.export_catalog.done'

    status = fields.Char('Status', readonly=True)
    submission_id = fields.Char('Submission ID', readonly=True)


class ExportAmazonCatalog(Wizard):
    '''Export catalog to Amazon

    Export the products selected to this amazon account
    '''
    __name__ = 'amazon.export_catalog'

    start = StateView(
        'amazon.export_catalog.start',
        'amazon_mws.export_catalog_start', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Continue', 'export_', 'tryton-ok', default=True),
        ]
    )
    export_ = StateTransition()
    done = StateView(
        'amazon.export_catalog.done',
        'amazon_mws.export_catalog_done', [
            Button('OK', 'end', 'tryton-cancel'),
        ]
    )

    def transition_export_(self):
        """
        Export the products selected to this amazon account
        """
        SaleChannel = Pool().get('sale.channel')

        amazon_channel = SaleChannel(Transaction().context.get('active_id'))

        response = amazon_channel.export_catalog_to_amazon()

        Transaction().set_context({'response': response})

        return 'done'

    def default_done(self, fields):
        "Display response"
        response = Transaction().context['response']
        return {
            'status': response['FeedSubmissionInfo'][
                'FeedProcessingStatus'
            ]['value'],
            'submission_id': response['FeedSubmissionInfo'][
                'FeedSubmissionId'
            ]['value']
        }


class ExportAmazonPricingStart(ModelView):
    'Export Catalog Pricing to Amazon View'
    __name__ = 'amazon.export_catalog_pricing.start'


class ExportAmazonPricingDone(ModelView):
    'Export Catalog Pricing to Amazon Done View'
    __name__ = 'amazon.export_catalog_pricing.done'

    status = fields.Char('Status', readonly=True)
    submission_id = fields.Char('Submission ID', readonly=True)


class ExportAmazonPricing(Wizard):
    '''Export catalog pricing to Amazon

    Export the prices products selected to this amazon account
    '''
    __name__ = 'amazon.export_catalog_pricing'

    start = StateView(
        'amazon.export_catalog_pricing.start',
        'amazon_mws.export_catalog_pricing_start', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Continue', 'export_', 'tryton-ok', default=True),
        ]
    )
    export_ = StateTransition()
    done = StateView(
        'amazon.export_catalog_pricing.done',
        'amazon_mws.export_catalog_pricing_done', [
            Button('OK', 'end', 'tryton-cancel'),
        ]
    )

    def transition_export_(self):
        """
        Export the prices for products selected to this amazon account
        """
        SaleChannel = Pool().get('sale.channel')

        amazon_channel = SaleChannel(Transaction().context.get('active_id'))

        response = amazon_channel.export_pricing_to_amazon()

        Transaction().set_context({'response': response})

        return 'done'

    def default_done(self, fields):
        "Display response"
        response = Transaction().context['response']
        return {
            'status': response['FeedSubmissionInfo'][
                'FeedProcessingStatus'
            ]['value'],
            'submission_id': response['FeedSubmissionInfo'][
                'FeedSubmissionId'
            ]['value']
        }


class ExportAmazonInventoryStart(ModelView):
    'Export Catalog Inventory to Amazon View'
    __name__ = 'amazon.export_catalog_inventory.start'


class ExportAmazonInventoryDone(ModelView):
    'Export Catalog Inventory to Amazon Done View'
    __name__ = 'amazon.export_catalog_inventory.done'

    status = fields.Char('Status', readonly=True)
    submission_id = fields.Char('Submission ID', readonly=True)


class ExportAmazonInventory(Wizard):
    '''Export catalog inventory to Amazon

    Export the prices products selected to this amazon account
    '''
    __name__ = 'amazon.export_catalog_inventory'

    start = StateView(
        'amazon.export_catalog_inventory.start',
        'amazon_mws.export_catalog_inventory_start', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Continue', 'export_', 'tryton-ok', default=True),
        ]
    )
    export_ = StateTransition()
    done = StateView(
        'amazon.export_catalog_inventory.done',
        'amazon_mws.export_catalog_inventory_done', [
            Button('OK', 'end', 'tryton-cancel'),
        ]
    )

    def transition_export_(self):
        """
        Export the prices for products selected to this amazon account
        """
        SaleChannel = Pool().get('sale.channel')

        amazon_channel = SaleChannel(Transaction().context.get('active_id'))

        response = amazon_channel.export_inventory_to_amazon()

        Transaction().set_context({'response': response})

        return 'done'

    def default_done(self, fields):
        "Display response"
        response = Transaction().context['response']
        return {
            'status': response['FeedSubmissionInfo'][
                'FeedProcessingStatus'
            ]['value'],
            'submission_id': response['FeedSubmissionInfo'][
                'FeedSubmissionId'
            ]['value']
        }
