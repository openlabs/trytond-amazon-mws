# -*- coding: utf-8 -*-
"""
    channle.py

    :copyright: (c) 2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from datetime import datetime
from dateutil.relativedelta import relativedelta
from mws import mws
from lxml import etree
from lxml.builder import E

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, Button, StateAction
from trytond.transaction import Transaction
from trytond.pyson import Eval
from trytond.pool import Pool, PoolMeta
from trytond.pyson import PYSONEncoder

__metaclass__ = PoolMeta

__all__ = [
    'SaleChannel', 'CheckAmazonServiceStatusView', 'CheckAmazonServiceStatus',
    'CheckAmazonSettingsView', 'CheckAmazonSettings', 'ImportAmazonOrdersView',
    'ImportAmazonOrders',
]

AMAZON_MWS_STATES = {
    'required': Eval('source') == 'amazon_mws',
    'invisible': ~(Eval('source') == 'amazon_mws')
}


class SaleChannel:
    "Amazon MWS Account"
    __name__ = 'sale.channel'

    # These are the credentials that you receive when you register a seller
    # account with Amazon MWS
    amazon_merchant_id = fields.Char(
        "Merchant ID", states=AMAZON_MWS_STATES, depends=['source']
    )
    amazon_marketplace_id = fields.Char(
        "MarketPlace ID", states=AMAZON_MWS_STATES, depends=['source']
    )
    amazon_access_key = fields.Char(
        "Access Key", states=AMAZON_MWS_STATES, depends=['source']
    )
    amazon_secret_key = fields.Char(
        "Secret Key", states=AMAZON_MWS_STATES, depends=['source']
    )

    last_amazon_order_import_time = fields.DateTime(
        'Last Amazon Order Import Time', states={
            'invisible': ~(Eval('source') == 'amazon_mws')
        }, depends=['source']
    )

    last_amazon_product_export_time = fields.DateTime(
        'Last Amazon Product Export Time', states={
            'invisible': ~(Eval('source') == 'amazon_mws')
        }, depends=['source']
    )

    @staticmethod
    def default_last_amazon_order_import_time():
        """
        Sets default last order import time
        """
        return datetime.utcnow() - relativedelta(days=30)

    @classmethod
    def get_source(cls):
        """
        Get the source
        """
        sources = super(SaleChannel, cls).get_source()

        sources.append(('amazon_mws', 'Amazon Marketplace'))

        return sources

    @staticmethod
    def default_default_uom():
        UoM = Pool().get('product.uom')

        unit = UoM.search([
            ('name', '=', 'Unit'),
        ])
        return unit and unit[0].id or None

    @classmethod
    def __setup__(cls):
        """
        Setup the class before adding to pool
        """
        super(SaleChannel, cls).__setup__()
        cls._buttons.update({
            'check_amazon_service_status': {},
            'check_amazon_settings': {},
            'import_amazon_orders_button': {},
        })

        cls._error_messages.update({
            'orders_not_found': 'No orders seems to be placed after %s',
            "missing_product_codes": (
                'Product "%(product)s" misses Amazon Product Identifiers'
            ),
            "missing_product_code": (
                'Product "%(product)s" misses Product Code'
            ),
            'invalid_channel': 'Channel does not belong to Amazon.'
        })

    def validate_amazon_channel(self):
        """
        Check if channel belongs to amazon mws
        """
        if self.source != 'amazon_mws':
            self.raise_user_error('invalid_channel')

    def get_mws_api(self):
        """
        Create an instance of mws api

        :return: mws api instance
        """
        return mws.MWS(
            access_key=self.amazon_access_key,
            secret_key=self.amazon_secret_key,
            account_id=self.amazon_merchant_id,
        )

    def get_amazon_order_api(self):
        """
        Create an instance of Order api

        :return: order api instance
        """
        return mws.Orders(
            access_key=self.amazon_access_key,
            secret_key=self.amazon_secret_key,
            account_id=self.amazon_merchant_id,
        )

    def get_amazon_product_api(self):
        """
        Create an instance of product api

        :return: Product API instance
        """
        return mws.Products(
            access_key=self.amazon_access_key,
            secret_key=self.amazon_secret_key,
            account_id=self.amazon_merchant_id,
        )

    def get_amazon_feed_api(self):
        """
        Return an instance of feed api
        """
        return mws.Feeds(
            access_key=self.amazon_access_key,
            secret_key=self.amazon_secret_key,
            account_id=self.amazon_merchant_id,
        )

    @classmethod
    @ModelView.button_action('amazon_mws.check_amazon_service_status')
    def check_amazon_service_status(cls, channels):
        """
        Check GREEN, GREEN_I, YELLOW or RED status

        :param channels: Active record list of sale channels
        """
        pass

    @classmethod
    @ModelView.button_action('amazon_mws.check_amazon_settings')
    def check_amazon_settings(cls, channels):
        """
        Checks account settings configured

        :param accounts: Active record list of sale channels
        """
        pass

    @classmethod
    def import_amazon_orders_using_cron(cls):
        """
        Cron method to import amazon orders
        """
        channels = cls.search([('source', '=', 'amazon_mws')])

        for channel in channels:
            channel.import_amazon_orders()

    def import_amazon_orders(self):
        """
        Import Orders for current channel
        """
        Sale = Pool().get('sale.sale')

        self.validate_amazon_channel()

        order_api = self.get_amazon_order_api()

        sales = []
        last_import_time = self.last_amazon_order_import_time.isoformat()

        response = order_api.list_orders(
            marketplaceids=[self.amazon_marketplace_id],
            created_after=last_import_time,
            orderstatus=('Unshipped', 'PartiallyShipped', 'Shipped')
        ).parsed

        if not response.get('Orders'):
            self.raise_user_error('orders_not_found', last_import_time)

        # Orders are returned as dictionary for single order and as
        # list for multiple orders.
        # Convert to list if dictionary is returned
        if isinstance(response['Orders']['Order'], dict):
            orders = [response['Orders']['Order']]
        else:
            orders = response['Orders']['Order']

        with Transaction().set_context({'current_channel': self.id}):
            for order_data in orders:
                sales.append(
                    Sale.find_or_create_using_amazon_id(
                        order_data['AmazonOrderId']['value']
                    )
                )

        # Update last order import time for channel
        self.write([self], {'last_amazon_order_import_time': datetime.utcnow()})

        return sales

    @classmethod
    @ModelView.button_action('amazon_mws.import_amazon_orders')
    def import_amazon_orders_button(cls, channels):
        """
        Import orders for current account
        """
        pass

    def _get_amazon_envelop(self, message_type, xml_list):
        """
        Returns amazon envelop for xml given
        """
        NS = "http://www.w3.org/2001/XMLSchema-instance"
        location_attribute = '{%s}noNamespaceSchemaLocation' % NS

        envelope_xml = E.AmazonEnvelope(
            E.Header(
                E.DocumentVersion('1.01'),
                E.MerchantIdentifier(self.amazon_merchant_id)
            ),
            E.MessageType(message_type),
            E.PurgeAndReplace('false'),
            *(xml for xml in xml_list)
        )
        envelope_xml.set(location_attribute, 'amznenvelope.xsd')

        return envelope_xml

    @classmethod
    def export_to_amazon_using_cron(cls):
        """
        Cron method to export product catalog to amazon
        """
        channels = cls.search([('source', '=', 'amazon_mws')])

        for channel in channels:
            channel.export_catalog_to_amazon(silent=True)

    @classmethod
    def export_prices_to_amazon_using_cron(cls):
        """
        Cron method to export product prices to amazon
        """
        channels = cls.search([('source', '=', 'amazon_mws')])

        for channel in channels:
            channel.export_pricing_to_amazon(silent=True)

    @classmethod
    def export_inventory_to_amazon_using_cron(cls):
        """
        Cron method to export product inventory to amazon
        """
        channels = cls.search([('source', '=', 'amazon_mws')])

        for channel in channels:
            channel.export_inventory_to_amazon(silent=True)

    def export_catalog_to_amazon(self, silent=False):
        """
        Export the products to the Amazon account in context
        """
        Product = Pool().get('product.product')

        self.validate_amazon_channel()

        domain = [
            ('template.export_to_amazon', '=', True),
            ('code', '!=', None),
            ('codes', 'not in', []),
        ]

        if self.last_amazon_product_export_time:
            domain.append(
                ('write_date', '>=', self.last_amazon_product_export_time)
            )

        products = Product.search(domain)

        products_xml = []
        for product in products:
            if not product.code:
                if silent:
                    return
                self.raise_user_error(
                    'missing_product_code', {
                        'product': product.template.name
                    }
                )
            if not product.codes:
                if silent:
                    return
                self.raise_user_error(
                    'missing_product_codes', {
                        'product': product.template.name
                    }
                )
            # Get the product's code to be set as standard ID to amazon
            product_standard_id = (
                product.asin or product.ean or product.upc or product.isbn
                or product.gtin
            )
            products_xml.append(E.Message(
                E.MessageID(str(product.id)),
                E.OperationType('Update'),
                E.Product(
                    E.SKU(product.code),
                    E.StandardProductID(
                        E.Type(product_standard_id.code_type.upper()),
                        E.Value(product_standard_id.code),
                    ),
                    E.DescriptionData(
                        E.Title(product.template.name),
                        E.Description(product.description),
                    ),
                    # Amazon needs this information so as to place the product
                    # under a category.
                    # FIXME: Either we need to create all that inside our
                    # system or figure out a way to get all that via API
                    E.ProductData(
                        E.Miscellaneous(
                            E.ProductType('Misc_Other'),
                        ),
                    ),
                )
            ))

        envelope_xml = self._get_amazon_envelop('Product', products_xml)

        feeds_api = self.get_amazon_feed_api()

        response = feeds_api.submit_feed(
            etree.tostring(envelope_xml),
            feed_type='_POST_PRODUCT_DATA_',
            marketplaceids=[self.amazon_marketplace_id]
        )

        # Update last product export time for channel
        self.write([self], {
            'last_amazon_product_export_time': datetime.utcnow()
        })

        Product.write(products, {
            'channel_listings': [
                ('create', [{
                    'channel': self.id,
                }])
            ]
        })

        return response.parsed

    def export_pricing_to_amazon(self, silent=False):
        """Export prices of the products to the Amazon account in context

        :param products: List of active records of products
        """
        Product = Pool().get('product.product')

        self.validate_amazon_channel()

        products = Product.search([
            ('code', '!=', None),
            ('codes', 'not in', []),
            ('channel_listings.channel', '=', self.id),
        ])

        pricing_xml = []
        for product in products:
            if self in [
                ch.channel for ch in product.channel_listings
            ]:
                pricing_xml.append(E.Message(
                    E.MessageID(str(product.id)),
                    E.OperationType('Update'),
                    E.Price(
                        E.SKU(product.code),
                        E.StandardPrice(
                            # TODO: Use a pricelist
                            str(product.template.list_price),
                            currency=self.company.currency.code
                        ),
                    )
                ))

        envelope_xml = self._get_amazon_envelop('Price', pricing_xml)

        feeds_api = self.get_amazon_feed_api()

        response = feeds_api.submit_feed(
            etree.tostring(envelope_xml),
            feed_type='_POST_PRODUCT_PRICING_DATA_',
            marketplaceids=[self.amazon_marketplace_id]
        )

        return response.parsed

    def export_inventory_to_amazon(self, silent=False):
        """Export inventory of the products to the Amazon account in context

        :param products: List of active records of products
        """
        Product = Pool().get('product.product')

        self.validate_amazon_channel()

        products = Product.search([
            ('code', '!=', None),
            ('codes', 'not in', []),
            ('channel_listings.channel', '=', self.id),
        ])

        inventory_xml = []
        for product in products:
            with Transaction().set_context({'locations': [self.warehouse.id]}):
                quantity = product.quantity

            if not quantity:
                continue

            if self in [
                ch.channel for ch in product.channel_listings
            ]:
                inventory_xml.append(E.Message(
                    E.MessageID(str(product.id)),
                    E.OperationType('Update'),
                    E.Inventory(
                        E.SKU(product.code),
                        E.Quantity(str(round(quantity))),
                        E.FulfillmentLatency(
                            str(product.template.delivery_time)
                        ),
                    )
                ))

        envelope_xml = self._get_amazon_envelop('Inventory', inventory_xml)

        feeds_api = self.get_amazon_feed_api()

        response = feeds_api.submit_feed(
            etree.tostring(envelope_xml),
            feed_type='_POST_INVENTORY_AVAILABILITY_DATA_',
            marketplaceids=[self.amazon_marketplace_id]
        )

        return response.parsed


class CheckAmazonServiceStatusView(ModelView):
    "Check Service Status View"
    __name__ = 'channel.check_amazon_service_status.view'

    status = fields.Char('Status', readonly=True)
    message = fields.Text("Message", readonly=True)


class CheckAmazonServiceStatus(Wizard):
    """
    Check Service Status Wizard

    Check service status for the current MWS account
    """
    __name__ = 'channel.check_amazon_service_status'

    start = StateView(
        'channel.check_amazon_service_status.view',
        'amazon_mws.check_amazon_service_status_view_form',
        [
            Button('OK', 'end', 'tryton-ok'),
        ]
    )

    def default_start(self, data):
        """
        Check the service status of the MWS account

        :param data: Wizard data
        """
        SaleChannel = Pool().get('sale.channel')

        channel = SaleChannel(Transaction().context.get('active_id'))

        res = {}
        api = channel.get_mws_api()
        response = api.get_service_status().parsed

        status = response['Status']['value']

        if status == 'GREEN':
            status_message = 'The service is operating normally. '

        elif status == 'GREEN_I':
            status_message = 'The service is operating normally. '

        elif status == 'YELLOW':
            status_message = 'The service is experiencing higher than ' + \
                'normal error rates or is operating with degraded performance. '
        else:
            status_message = 'The service is unavailable or experiencing ' + \
                'extremely high error rates. '

        res['status'] = status
        if not response.get('Messages'):
            res['message'] = status_message
            return res

        if isinstance(response['Messages']['Message'], dict):
            messages = [response['Messages']['Message']]
        else:
            messages = response['Messages']['Message']

        for message in messages:
            status_message = status_message + message['Text']['value'] + ' '
            res['message'] = status_message

        return res


class CheckAmazonSettingsView(ModelView):
    "Check Amazon Settings View"
    __name__ = 'channel.check_amazon_settings.view'

    status = fields.Text('Status', readonly=True)


class CheckAmazonSettings(Wizard):
    """
    Wizard to Check Amazon MWS Settings

    Check amazon settings configured for the current MWS account
    """
    __name__ = 'channel.check_amazon_settings'

    start = StateView(
        'channel.check_amazon_settings.view',
        'amazon_mws.check_amazon_settings_view_form',
        [
            Button('OK', 'end', 'tryton-ok'),
        ]
    )

    def default_start(self, data):
        """
        Check the amazon settings for the current account

        :param data: Wizard data
        """
        SaleChannel = Pool().get('sale.channel')

        channel = SaleChannel(Transaction().context.get('active_id'))

        channel.validate_amazon_channel()

        res = {}
        api = channel.get_amazon_feed_api()

        try:
            api.get_feed_submission_count().parsed
            res['status'] = 'Account settings have been configured correctly'

        except mws.MWSError:
            res['status'] = "Something went wrong. Please check account " + \
                "settings again"
        return res


class ImportAmazonOrdersView(ModelView):
    "Import Orders View"
    __name__ = 'channel.import_amazon_orders.view'

    message = fields.Text("Message", readonly=True)


class ImportAmazonOrders(Wizard):
    """
    Import Amazon Orders Wizard

    Import orders for the current amazon channel
    """
    __name__ = 'channel.import_amazon_orders'

    start = StateView(
        'channel.import_amazon_orders.view',
        'amazon_mws.import_amazon_orders_view_form',
        [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Continue', 'import_', 'tryton-ok', default=True),
        ]
    )

    import_ = StateAction('sale.act_sale_form')

    def default_start(self, data):
        """
        Sets default data for wizard
        """
        return {
            'message':
                'This wizard will import orders for this seller '
                'account. It imports orders updated only after Last Order '
                'Import Time.'
        }

    def do_import_(self, action):
        """
        Import orders and open records created
        """
        SaleChannel = Pool().get('sale.channel')

        channel = SaleChannel(Transaction().context.get('active_id'))
        channel.validate_amazon_channel()

        sales = channel.import_amazon_orders()

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', map(int, sales))
        ])
        return action, {}

    def transition_import_(self):
        return 'end'
