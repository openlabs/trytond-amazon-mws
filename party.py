# -*- coding: utf-8 -*-
"""
    party

    Party

    :copyright: (c) 2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.model import fields
from trytond.pool import PoolMeta, Pool


__all__ = ['Party', 'Address']
__metaclass__ = PoolMeta


class Party:
    "Party"
    __name__ = 'party.party'

    amazon_user_email = fields.Char(
        'Amazon Email', readonly=True,
        help="This is global and unique email given to a user across whole "
        "amazon. "
        "Warning: Editing this might result in duplication of parties on next"
        " import"
    )

    @classmethod
    def __setup__(cls):
        """
        Setup the class before adding to pool
        """
        super(Party, cls).__setup__()
        cls._error_messages.update({
            'account_not_found': 'Amazon Account does not exist in context',
        })

        cls._sql_constraints += [
            (
                'amazon_id_unique',
                'UNIQUE(amazon_user_email)',
                'Party with this amazon Order ID already exists'
            )
        ]

    @classmethod
    def find_or_create_using_amazon_data(cls, amazon_data):
        """
        Creates record of customer values sent by amazon

        :param amazon_data: Dictionary of values for customer sent by amazon
        :return: Active record of record created
        """
        parties = cls.search([
            ('amazon_user_email', '=', amazon_data['email']),
        ])
        if parties:
            return parties[0]

        return cls.create_using_amazon_data(amazon_data)

    @classmethod
    def create_using_amazon_data(cls, amazon_data):
        """
        Creates record of customer values sent by amazon

        :param amazon_data: Dictionary of values for customer sent by amazon
        :return: Active record of record created
        """
        return cls.create([{
            'name': amazon_data['name'],
            'amazon_user_email': amazon_data['email'],
            'contact_mechanisms': [
                ('create', [{
                    'email': amazon_data['email']
                }])
            ]
        }])[0]

    def add_phone_using_amazon_data(self, amazon_phone):
        """
        Add contact mechanism for party
        """
        ContactMechanism = Pool().get('party.contact_mechanism')

        if not ContactMechanism.search([
            ('party', '=', self.id),
            ('type', 'in', ['phone', 'mobile']),
            ('value', '=', amazon_phone),
        ]):
            ContactMechanism.create([{
                'party': self.id,
                'type': 'phone',
                'value': amazon_phone,
            }])


class Address:
    "Address"
    __name__ = 'party.address'

    def is_match_found(self, amazon_address):
        """
        Match the current address with the address fetched from amazon.
        Match all the fields of the address, i.e., streets, city, subdivision
        and country. For any deviation in any field, returns False.

        :param amazon_address: Amazon address instance
        :return: True if address matches else False
        """
        return all([
            self.name == amazon_address.name,
            self.street == amazon_address.street,
            self.streetbis == amazon_address.streetbis,
            self.zip == amazon_address.zip,
            self.city == amazon_address.city,
            self.country == amazon_address.country,
            self.subdivision == amazon_address.subdivision,
        ])

    @classmethod
    def find_or_create_for_party_using_amazon_data(cls, party, address_data):
        """
        Look for the address in tryton corresponding to the address_record.
        If found, return the same else create a new one and return that.

        :param party: Party active record
        :param address_data: Dictionary of address data from amazon
        :return: Active record of address created/found
        """
        amazon_address = cls.get_address_from_amazon_data(party, address_data)

        for address in party.addresses:
            if address.is_match_found(amazon_address):
                return address

        else:
            # Create new address
            amazon_address.save()
            return amazon_address

    @classmethod
    def get_address_from_amazon_data(cls, party, address_data):
        """
        Return address instance for data fetched from amazon
        """
        Address = Pool().get('party.address')
        Country = Pool().get('country.country')
        Subdivision = Pool().get('country.subdivision')

        country, = Country.search([
            ('code', '=', address_data['CountryCode']['value'])
        ], limit=1)
        subdivision = Subdivision.search_using_amazon_state(
            address_data['StateOrRegion']['value'], country
        )

        return Address(
            party=party.id,
            name=address_data['Name']['value'],
            street=address_data['AddressLine1']['value'],
            streetbis=(
                address_data.get('AddressLine2') and
                address_data['AddressLine2'].get('value') or None
            ),
            zip=address_data['PostalCode']['value'],
            city=address_data['City']['value'],
            country=country.id,
            subdivision=subdivision.id,
        )
