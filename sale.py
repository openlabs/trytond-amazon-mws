# -*- coding: utf-8 -*-
"""
    sale

    Sale

    :copyright: (c) 2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import dateutil.parser
from decimal import Decimal

from trytond.model import fields
from trytond.transaction import Transaction
from trytond.pool import PoolMeta, Pool


__all__ = ['Sale']
__metaclass__ = PoolMeta


class Sale:
    "Sale"
    __name__ = 'sale.sale'

    amazon_order_id = fields.Char(
        'Amazon Order ID', readonly=True, select=True,
        help="This is global and unique ID given to an order across whole"
        "amazon"
        "Warning: Editing this might result in duplicate orders on next"
        " import"
    )

    @classmethod
    def __setup__(cls):
        """
        Setup the class before adding to pool
        """
        super(Sale, cls).__setup__()

        cls._sql_constraints += [
            (
                'amazon_id_unique',
                'UNIQUE(amazon_order_id)',
                'Sale with this amazon Order ID already exists'
            )
        ]

    @classmethod
    def find_or_create_using_amazon_id(cls, order_id):
        """
        This method tries to find the sale with the order ID
        first and if not found it will fetch the info from amazon and
        create a new sale with the data from amazon using
        create_using_amazon_data

        :param order_id: Order ID from amazon
        :type order_id: string
        :returns: Active record of sale order created/found
        """
        SaleChannel = Pool().get('sale.channel')

        sales = cls.search([
            ('amazon_order_id', '=', order_id),
        ])
        if sales:
            return sales[0]

        amazon_channel = SaleChannel(
            Transaction().context.get('amazon_channel')
        )
        order_api = amazon_channel.get_order_api()

        order_data = order_api.get_order([order_id]).parsed

        order_line_data = order_api.list_order_items(
            order_data['Orders']['Order']['AmazonOrderId']['value']
        ).parsed

        return cls.create_using_amazon_data(
            order_data['Orders']['Order'],
            order_line_data['OrderItems']['OrderItem']
        )

    @classmethod
    def create_using_amazon_data(cls, order_data, line_data):
        """
        Create a sale using amazon data

        :param order_data: Order data from amazon
        :return: Active record of record created
        """
        Party = Pool().get('party.party')
        Address = Pool().get('party.address')
        SaleChannel = Pool().get('sale.channel')
        Currency = Pool().get('currency.currency')
        Uom = Pool().get('product.uom')

        amazon_channel = SaleChannel(
            Transaction().context.get('amazon_channel')
        )

        currency, = Currency.search([
            ('code', '=', order_data['OrderTotal']['CurrencyCode']['value'])
        ], limit=1)

        # Order lines are returned as dictionary for single record and as list
        # for mulitple reocrds.
        # So convert to list if its dictionary
        if isinstance(line_data, dict):
            # If its a single line order, then the array will be dict
            order_items = [line_data]
        else:
            # In case of multi line orders, the transaction array will be
            # a list of dictionaries
            order_items = line_data

        party_values = {
            'name': order_data['BuyerEmail']['value'],
            'email': order_data['BuyerName']['value'],
        }
        party = Party.create_using_amazon_data(party_values)
        party.add_phone_using_amazon_data(
            order_data['ShippingAddress']['Phone']['value']
        )

        party_invoice_address = party_shipping_address = \
            Address.find_or_create_for_party_using_amazon_data(
                party, order_data['ShippingAddress']
            )
        unit, = Uom.search([('name', '=', 'Unit')])

        sale_data = {
            'reference': order_data['AmazonOrderId']['value'],
            'sale_date': dateutil.parser.parse(
                order_data['PurchaseDate']['value']
            ).date(),
            'party': party.id,
            'currency': currency.id,
            'invoice_address': party_invoice_address.id,
            'shipment_address': party_shipping_address.id,
            'amazon_order_id': order_data['AmazonOrderId']['value'],
            'lines': cls.get_item_line_data_using_amazon_data(order_items),
            'channel': amazon_channel.id,
        }

        for order_item in order_items:
            if order_item['ShippingPrice']['Amount']['value']:
                sale_data['lines'].append(
                    cls.get_shipping_line_data_using_amazon_data(order_item)
                )

        # TODO: Handle Discounts
        # TODO: Handle Taxes

        sale, = cls.create([sale_data])

        # Assert that the order totals are same
        assert sale.total_amount == Decimal(
            order_data['OrderTotal']['Amount']['value']) * Decimal(
            order_data['NumberOfItemsShipped']['value']
        )

        # We import only completed orders, so we can confirm them all
        cls.quote([sale])
        cls.confirm([sale])

        # TODO: Process the order for invoice as the payment info is received

        return sale

    @classmethod
    def get_item_line_data_using_amazon_data(cls, order_items):
        """
        Make data for an item line from the amazon data.

        :param order_items: Order items
        :return: List of data of order lines in required format
        """
        Uom = Pool().get('product.uom')
        Product = Pool().get('product.product')

        unit, = Uom.search([('name', '=', 'Unit')])

        line_data = []
        for order_item in order_items:
            line_data.append(
                ('create', [{
                    'description': order_item['Title']['value'],
                    'unit_price': Decimal(
                        order_item['ItemPrice']['Amount']['value']
                    ),
                    'unit': unit.id,
                    'quantity': Decimal(order_item['QuantityOrdered']['value']),
                    'product': Product.find_or_create_using_amazon_sku(
                        order_item['SellerSKU']['value'],
                    ).id
                }])
            )

        return line_data

    @classmethod
    def get_shipping_line_data_using_amazon_data(cls, order_item):
        """
        Create a shipping line for the given sale using amazon data

        :param order_item: Order Data from amazon
        """
        Uom = Pool().get('product.uom')

        unit, = Uom.search([('name', '=', 'Unit')])

        return (
            'create', [{
                'description': 'eBay Shipping and Handling',
                'unit_price': Decimal(
                    order_item['ShippingPrice']['Amount']['value']
                ),
                'unit': unit.id,
                'quantity': Decimal(
                    order_item['QuantityOrdered']['value']
                ),  # XXX: Not sure about this if shipping charges must
                    # be applied to each quantity ordered
            }]
        )
