# -*- coding: utf-8 -*-
"""
    amazon

    Amazon

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from mws import mws
from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateView, Button
from trytond.transaction import Transaction
from trytond.pool import Pool


__all__ = [
    'MWSAccount', 'CheckServiceStatusView', 'CheckServiceStatus',
    'CheckAmazonSettingsView', 'CheckAmazonSettings'
]


class MWSAccount(ModelSQL, ModelView):
    "Amazon MWS Account"
    __name__ = 'amazon.mws.account'

    # These are the credentials that you receive when you register a seller
    # account with Amazon MWS
    merchant_id = fields.Char("Merchant ID", required=True)
    marketplace_id = fields.Char("MarketPlace ID", required=True)
    access_key = fields.Char("Access Key", required=True)
    secret_key = fields.Char("Secret Key", required=True)

    company = fields.Many2One("company.company", "Company", required=True)

    warehouse = fields.Many2One(
        'stock.location', 'Warehouse',
        domain=[('type', '=', 'warehouse')], required=True
    )

    @classmethod
    def default_warehouse(cls):
        "Default value for warehouse"
        Location = Pool().get('stock.location')
        locations = Location.search(cls.warehouse.domain)
        if len(locations) == 1:
            return locations[0].id

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @classmethod
    def __setup__(cls):
        """
        Setup the class before adding to pool
        """
        super(MWSAccount, cls).__setup__()
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

    @classmethod
    @ModelView.button_action('amazon_mws.check_service_status')
    def check_service_status(cls, accounts):
        """
        Check GREEN, GREEN_I, YELLOW or RED status

        :param accounts: Active record list of amazon mws accounts
        """
        pass

    @classmethod
    @ModelView.button_action('amazon_mws.check_amazon_settings')
    def check_amazon_settings(cls, accounts):
        """
        Checks account settings configured

        :param accounts: Active record list of amazon mws accounts
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
        MWSAccount = Pool().get('amazon.mws.account')

        account = MWSAccount(Transaction().context.get('active_id'))

        res = {}
        api = account.get_mws_api()
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
        MWSAccount = Pool().get('amazon.mws.account')

        account = MWSAccount(Transaction().context.get('active_id'))

        res = {}
        api = mws.Feeds(
            access_key=account.access_key,
            secret_key=account.secret_key,
            account_id=account.merchant_id,
        )

        try:
            api.get_feed_submission_count().parsed
            res['status'] = 'Account settings have been configured correctly'

        except mws.MWSError:
            res['status'] = "Something went wrong. Please check account " + \
                "settings again"
        return res
