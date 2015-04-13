# -*- coding: utf-8 -*-
"""
    channle.py

    :copyright: (c) 2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from datetime import datetime
from dateutil.relativedelta import relativedelta
from mws import mws

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, Button, StateAction
from trytond.transaction import Transaction
from trytond.pyson import Eval
from trytond.pool import Pool, PoolMeta
from trytond.pyson import PYSONEncoder

__metaclass__ = PoolMeta

__all__ = [
    'SaleChannel', 'CheckServiceStatusView', 'CheckServiceStatus',
    'CheckAmazonSettingsView', 'CheckAmazonSettings', 'ImportOrdersView',
    'ImportOrders',
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
    merchant_id = fields.Char(
        "Merchant ID", states=AMAZON_MWS_STATES, depends=['source']
    )
    marketplace_id = fields.Char(
        "MarketPlace ID", states=AMAZON_MWS_STATES, depends=['source']
    )
    access_key = fields.Char(
        "Access Key", states=AMAZON_MWS_STATES, depends=['source']
    )
    secret_key = fields.Char(
        "Secret Key", states=AMAZON_MWS_STATES, depends=['source']
    )

    default_uom = fields.Many2One(
        'product.uom', 'Default Product UOM',
        states=AMAZON_MWS_STATES, depends=['source']
    )
    default_account_expense = fields.Property(fields.Many2One(
        'account.account', 'Account Expense', domain=[
            ('kind', '=', 'expense'),
            ('company', '=', Eval('company')),
        ], states=AMAZON_MWS_STATES, depends=['company', 'source'],
    ))

    #: Used to set revenue account while creating products.
    default_account_revenue = fields.Property(fields.Many2One(
        'account.account', 'Account Revenue', domain=[
            ('kind', '=', 'revenue'),
            ('company', '=', Eval('company')),
        ], states=AMAZON_MWS_STATES, depends=['source', 'company']
    ))
    last_order_import_time = fields.DateTime(
        'Last Order Import Time', states=AMAZON_MWS_STATES, depends=['source']
    )

    @staticmethod
    def default_last_order_import_time():
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
            'check_service_status': {},
            'check_amazon_settings': {},
            'import_orders_button': {},
        })

        cls._error_messages.update({
            'orders_not_found': 'No orders seems to be placed after %s'
        })

    def get_mws_api(self):
        """
        Create an instance of mws api

        :return: mws api instance
        """
        return mws.MWS(
            access_key=self.access_key,
            secret_key=self.secret_key,
            account_id=self.merchant_id,
        )

    def get_amazon_order_api(self):
        """
        Create an instance of Order api

        :return: order api instance
        """
        return mws.Orders(
            access_key=self.access_key,
            secret_key=self.secret_key,
            account_id=self.merchant_id,
        )

    def get_amazon_product_api(self):
        """
        Create an instance of product api

        :return: Product API instance
        """
        return mws.Products(
            access_key=self.access_key,
            secret_key=self.secret_key,
            account_id=self.merchant_id,
        )

    def get_amazon_feed_api(self):
        """
        Return an instance of feed api
        """
        return mws.Feeds(
            access_key=self.access_key,
            secret_key=self.secret_key,
            account_id=self.merchant_id,
        )

    @classmethod
    @ModelView.button_action('amazon_mws.check_service_status')
    def check_service_status(cls, channels):
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

    def import_orders(self):
        """
        Import Orders for current channel
        """
        Sale = Pool().get('sale.sale')

        order_api = self.get_amazon_order_api()

        sales = []
        last_import_time = self.last_order_import_time.isoformat()

        response = order_api.list_orders(
            marketplaceids=[self.marketplace_id],
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
        self.write([self], {'last_order_import_time': datetime.utcnow()})

        return sales

    @classmethod
    @ModelView.button_action('amazon_mws.import_amazon_orders')
    def import_orders_button(cls, channels):
        """
        Import orders for current account
        """
        pass


class CheckServiceStatusView(ModelView):
    "Check Service Status View"
    __name__ = 'amazon.mws.check_service_status.view'

    status = fields.Char('Status', readonly=True)
    message = fields.Text("Message", readonly=True)


class CheckServiceStatus(Wizard):
    """
    Check Service Status Wizard

    Check service status for the current MWS account
    """
    __name__ = 'amazon.mws.check_service_status'

    start = StateView(
        'amazon.mws.check_service_status.view',
        'amazon_mws.check_service_status_view_form',
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
    __name__ = 'amazon.mws.check_amazon_settings.view'

    status = fields.Text('Status', readonly=True)


class CheckAmazonSettings(Wizard):
    """
    Wizard to Check Amazon MWS Settings

    Check amazon settings configured for the current MWS account
    """
    __name__ = 'amazon.mws.check_amazon_settings'

    start = StateView(
        'amazon.mws.check_amazon_settings.view',
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

        res = {}
        api = mws.Feeds(
            access_key=channel.access_key,
            secret_key=channel.secret_key,
            account_id=channel.merchant_id,
        )

        try:
            api.get_feed_submission_count().parsed
            res['status'] = 'Account settings have been configured correctly'

        except mws.MWSError:
            res['status'] = "Something went wrong. Please check account " + \
                "settings again"
        return res


class ImportOrdersView(ModelView):
    "Import Orders View"
    __name__ = 'sale.channel.import_amazon_orders.view'

    message = fields.Text("Message", readonly=True)


class ImportOrders(Wizard):
    """
    Import Orders Wizard

    Import orders for the current MWS account
    """
    __name__ = 'sale.channel.import_amazon_orders'

    start = StateView(
        'sale.channel.import_amazon_orders.view',
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

        sales = channel.import_orders()

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', map(int, sales))
        ])
        return action, {}

    def transition_import_(self):
        return 'end'
