# -*- coding: utf-8 -*-
{
    'name': "advertising_order_print_revenue",

    'summary': """
        Advertising Order Print Revenue""",

    'description': """
        Advertising Order Print Revenue
    """,

    'author': 'Magnus - Willem Hulshof',
    'website': 'http://www.magnus.nl',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sale',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['sale_advertising_order',
                'account_invoice_start_end_dates'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}