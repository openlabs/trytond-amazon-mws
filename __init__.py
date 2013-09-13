# -*- coding: utf-8 -*-
"""
    __init__

    Initialize module

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool
from .amazon import (
    MWSAccount, CheckServiceStatus, CheckServiceStatusView
)


def register():
    """
    Register classes with pool
    """
    Pool.register(
        MWSAccount,
        CheckServiceStatusView,
        module='amazon_mws', type_='model'
    )

    Pool.register(
        CheckServiceStatus,
        module='amazon_mws', type_='wizard'
    )
