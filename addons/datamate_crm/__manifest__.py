# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'DatamateCRM',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'CPQ Engine — Configure, Price, Quote for Datamate Enterprise Products',
    'description': """
        Cumulative tax-bracket-style pricing engine based on hospital bed count.
        Supports multi-tiered proposals with RBAC-protected internal margins.
    """,
    'author': 'Datamate',
    'website': 'https://www.datamate.in',
    'depends': ['sale'],
    'data': [
        # Security (groups first, then access rights)
        'security/datamate_crm_security.xml',
        'security/ir.model.access.csv',
        # Report templates
        'report/ir_actions_report_templates.xml',
        # Views
        'views/product_pricing_tier_views.xml',
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/datamate_crm_menus.xml',
    ],
    'demo': [
        'data/product_demo.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
