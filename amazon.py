# -*- coding: utf-8 -*-
"""
    amazon

    Amazon

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.model import ModelView, ModelSQL, fields


__all__ = ['AmazonMWSAccount']


class AmazonMWSAccount(ModelSQL, ModelView):
    "Amazon MWS Account"
    __name__ = 'amazon.mws.account'

    # These are the credentials that you receive when you register a seller
    # account with Amazon MWS
    merchant_id = fields.Char("Merchant ID", required=True)
    marketplace_id = fields.Char("MarketPlace ID", required=True)
    access_key = fields.Char("Access Key", required=True)
    secret_key = fields.Char("Secret Key", required=True)
