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
from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT
from trytond.transaction import Transaction


class TestAmazon(unittest.TestCase):
    "Test Amazon"

    def setUp(self):
        """
        Set up data used in the tests.
        this method is called before each test function execution.
        """
        trytond.tests.test_tryton.install_module('amazon_mws')

    def test_0010_create_amazon_account(self):
        """
        Create amazon mws account
        """
        AmazonAccount = POOL.get('amazon.mws.account')
        Company = POOL.get('company.company')
        User = POOL.get('res.user')
        Party = POOL.get('party.party')
        Currency = POOL.get('currency.currency')
        Location = POOL.get('stock.location')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            with Transaction().set_context(company=None):
                party, = Party.create([{
                    'name': 'ABC',
                }])
                usd, = Currency.create([{
                    'name': 'US Dollar',
                    'code': 'USD',
                    'symbol': '$',
                }])
                company, = Company.create([{
                    'party': party.id,
                    'currency': usd.id,
                }])

            User.write([User(USER)], {
                'main_company': company.id,
                'company': company.id,
            })

            warehouse, = Location.search([
                ('type', '=', 'warehouse')
            ], limit=1)

            account = AmazonAccount.create([{
                'merchant_id': '1234',
                'marketplace_id': '3456',
                'access_key': 'AWS1',
                'secret_key': 'S013',
                'company': company.id,
                'warehouse': warehouse.id,
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
