# -*- coding: utf-8 -*-
"""
    channle.py

    :copyright: (c) 2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from mws import mws
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, Button
from trytond.transaction import Transaction
from trytond.pyson import Eval
from trytond.pool import Pool, PoolMeta

__metaclass__ = PoolMeta

__all__ = [
    'SaleChannel', 'CheckServiceStatusView', 'CheckServiceStatus',
    'CheckAmazonSettingsView', 'CheckAmazonSettings'
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

    def get_product_api(self):
        """
        Create an instance of product api

        :return: Product API instance
        """
        return mws.Products(
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
