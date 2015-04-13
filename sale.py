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
from trytond.pyson import Eval


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
        " import",
        states={
            'invisible': ~(Eval('channel_type') == 'amazon_mws')
        }, depends=['channel_type']
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
            Transaction().context['current_channel']
        )
        assert amazon_channel.source == 'amazon_mws'

        order_api = amazon_channel.get_amazon_order_api()

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

        amazon_channel = SaleChannel(
            Transaction().context['current_channel']
        )
        assert amazon_channel.source == 'amazon_mws'

        party_values = {
            'name': order_data['BuyerEmail']['value'],
            'email': order_data['BuyerName']['value'],
        }
        party = Party.find_or_create_using_amazon_data(party_values)

        party.add_phone_using_amazon_data(
            order_data['ShippingAddress']['Phone']['value']
        )
        party_invoice_address = party_shipping_address = \
            Address.find_or_create_for_party_using_amazon_data(
                party, order_data['ShippingAddress']
            )

        sale = cls.get_sale_using_amazon_data(order_data, line_data)

        sale.party = party.id
        sale.invoice_address = party_invoice_address.id
        sale.shipment_address = party_shipping_address.id
        sale.channel = amazon_channel.id
        sale.save()

        # TODO: Handle Discounts
        # TODO: Handle Taxes

        # Assert that the order totals are same
        # Cases handled according to OrderStatus
        # XXX: Handle case of PartiallyShipped
        if order_data['OrderStatus']['value'] == 'Unshipped':
            assert sale.total_amount == Decimal(
                order_data['OrderTotal']['Amount']['value']) * Decimal(
                order_data['NumberOfItemsUnshipped']['value']
            )
        elif order_data['OrderStatus']['value'] == 'Shipped':
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
    def get_sale_using_amazon_data(cls, order_data, line_data):
        """
        Returns sale for amazon order
        """
        Sale = Pool().get('sale.sale')
        Currency = Pool().get('currency.currency')
        currency, = Currency.search([
            ('code', '=', order_data['OrderTotal']['CurrencyCode']['value'])
        ], limit=1)

        return Sale(
            reference=order_data['AmazonOrderId']['value'],
            sale_date=dateutil.parser.parse(
                order_data['PurchaseDate']['value']
            ).date(),
            currency=currency.id,
            amazon_order_id=order_data['AmazonOrderId']['value'],
            lines=cls.get_item_line_data_using_amazon_data(line_data)
        )

    @classmethod
    def get_item_line_data_using_amazon_data(cls, line_data):
        """
        Make data for an item line from the amazon data.

        :param order_items: Order items
        :return: List of data of order lines in required format
        """
        Uom = Pool().get('product.uom')
        Product = Pool().get('product.product')
        SaleLine = Pool().get('sale.line')

        unit, = Uom.search([('name', '=', 'Unit')])

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

        sale_lines = []
        for order_item in order_items:
            sale_lines.append(
                SaleLine(
                    description=order_item['Title']['value'],
                    unit_price=Decimal(
                        order_item['ItemPrice']['Amount']['value']
                    ),
                    unit=unit.id,
                    quantity=Decimal(order_item['QuantityOrdered']['value']),
                    product=Product.find_or_create_using_amazon_sku(
                        order_item['SellerSKU']['value'],
                    ).id
                )
            )

            if order_item['ShippingPrice']['Amount']['value']:
                sale_lines.append(
                    cls.get_shipping_line_data_using_amazon_data(order_item)
                )

        return sale_lines

    @classmethod
    def get_shipping_line_data_using_amazon_data(cls, order_item):
        """
        Create a shipping line for the given sale using amazon data

        :param order_item: Order Data from amazon
        """
        SaleLine = Pool().get('sale.line')
        Uom = Pool().get('product.uom')

        unit, = Uom.search([('name', '=', 'Unit')])

        return SaleLine(
            description='Amazon Shipping and Handling',
            unit_price=Decimal(
                order_item['ShippingPrice']['Amount']['value']
            ),
            unit=unit.id,
            quantity=Decimal(
                order_item['QuantityOrdered']['value']
            ),  # XXX: Not sure about this if shipping charges must
                # be applied to each quantity ordered
        )
