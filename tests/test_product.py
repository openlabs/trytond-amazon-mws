# -*- coding: utf-8 -*-
"""
    test_product

    Tests Product

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import sys
import os
from decimal import Decimal
DIR = os.path.abspath(os.path.normpath(
    os.path.join(
        __file__,
        '..', '..', '..', '..', '..', 'trytond'
    )
))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))

import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT
from trytond.transaction import Transaction
from test_base import TestBase, load_json


class TestProduct(TestBase):
    '''
    Tests Product
    '''

    def test_0010_code_fields(self):
        """Tests the function fields for codes
        """
        Template = POOL.get('product.template')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()

            template, = Template.create([{
                'name': 'Test Product',
                'default_uom': self.uom.id,
                'list_price': Decimal('10.0'),
                'cost_price': Decimal('8.0'),
                'account_expense': self.get_account_by_kind('expense'),
                'account_revenue': self.get_account_by_kind('revenue'),
                'export_to_amazon': True,
                'products': [('create', [{
                    'code': 'code1',
                    'description': 'Some product description',
                    'codes': [('create', [{
                        'code': 'BUYGBS6866',
                        'code_type': 'asin',
                    }, {
                        'code': '123456789012',
                        'code_type': 'upc',
                    }, {
                        'code': '1234567890123',
                        'code_type': 'ean',
                    }])]
                }])]
            }])

            product, = template.products

            self.assertEqual(product.ean.code, '1234567890123')
            self.assertEqual(product.upc.code, '123456789012')
            self.assertEqual(product.asin.code, 'BUYGBS6866')

    def test_0020_create_product_using_amazon_data(self):
        """
        Tests if product is created using amazon data
        """
        Product = POOL.get('product.product')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()

            with Transaction().set_context(
                {'current_channel': self.sale_channel.id}
            ):
                self.assertEqual(Product.search([], count=True), 0)

                product_data = load_json('products', 'product-1')
                Product.create_using_amazon_data(product_data)

                self.assertEqual(Product.search([], count=True), 1)


def suite():
    """
    Test Suite
    """
    test_suite = trytond.tests.test_tryton.suite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestProduct)
    )
    return test_suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
