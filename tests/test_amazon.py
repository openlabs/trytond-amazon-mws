# -*- coding: utf-8 -*-
"""
    test_amazon

    Tests Amazon

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import os
import sys
import unittest
DIR = os.path.abspath(os.path.normpath(
    os.path.join(
        __file__,
        '..', '..', '..', '..', '..', 'trytond'
    )
))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))

import trytond.tests.test_tryton
from trytond.tests.test_tryton import USER, DB_NAME, CONTEXT, POOL
from test_base import TestBase
from trytond.transaction import Transaction


class TestAmazon(TestBase):
    "Test Amazon"

    def test_0010_create_amazon_account(self):
        """
        Create amazon mws account
        """
        Location = POOL.get('stock.location')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()

            warehouse, = Location.search([
                ('type', '=', 'warehouse')
            ], limit=1)

            account = self.MWSAccount.create([{
                'name': 'AmazonAccount',
                'merchant_id': '1234',
                'marketplace_id': '3456',
                'access_key': 'AWS1',
                'secret_key': 'S013',
                'warehouse': warehouse.id,
                'company': self.company.id,
                'default_account_revenue': self.get_account_by_kind('revenue'),
                'default_account_expense': self.get_account_by_kind('expense'),
                'shop': self.shop,
                'default_uom': self.uom,
            }])

            self.assert_(account)


def suite():
    """
    Test Suite
    """
    test_suite = trytond.tests.test_tryton.suite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestAmazon)
    )
    return test_suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
