# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
{
    'name': 'Trailer Reservations',
    'version': '1.0',
    'summary': 'Translation of the Assets Reservations module',
    'author': "BulkTP, InfoTerra",
    'maintainer': 'Elsie Vernon Hogan <evhogan3@gmail.com>, Antonio Buric <antonio.burich@gmail.com>',
    'category': 'Industries',
    'description': """
An Add-on for the Assets reservations module which changes the term asset with trailer system-wide.

==========================

Translations only.
""",
    'depends': [
        'asset_reservations',
    ],
    'website': '',
    'data': [
        'views/account_asset_view.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    #'images': ['static/description/banner.png']
}
