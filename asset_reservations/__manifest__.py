# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
{
    'name': 'Asset Reservations',
    'version': '1.0',
    'summary': 'Addon for the Assets Tracking module',
    'author': "BulkTP, InfoTerra",
    'maintainer': 'Elsie Vernon Hogan <evhogan3@gmail.com>, Antonio Buric <antonio.burich@gmail.com>',
    'category': 'Industries',
    'description': """
An Add-on for the Assets GPS tracking module which brings in reservations (can be used for any rental services like trailer rentals).

==========================

Keep track of your asset reservations.
""",
    'depends': [
        'traccar_person_assets_tracking',
        'sale_rental'
    ],
    'website': '',
    'data': [
        'security/ir.model.access.csv',
        'data/asset_reservation_sequence.xml',
        'data/email_template_data.xml',
        'data/ir_cron_data.xml',
        'views/reservation_assets.xml',
        'views/asset_reservation_template.xml',
        'views/account_asset_view.xml',
    ],
    'demo': [],
    'js': ['static/src/js/account_asset_summary.js', ],
    'qweb': ['static/src/xml/account_asset_summary.xml'],
    'css': ['static/src/css/asset_summary.css'],
    'installable': True,
    'application': True,
    #'images': ['static/description/banner.png']
}
