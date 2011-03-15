# encoding: utf-8
# Copyright 2009-2010 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

'''Old-style installation extra steps. It'll be nice when this can go away.'''

from Products.CMFCore.utils import getToolByName
import transaction

PRODUCT_DEPENDENCIES = (
    'p4a.subtyper',
    'eea.facetednavigation',
    # 'Products.CacheSetup', Leak?
    'LoginLockout',
    'plone.app.ldap',
    'edrn.theme',
    'edrnsite.portlets',
    'edrnsite.funding',
    'edrnsite.search',
    'edrnsite.misccontent',
    'eke.knowledge',
    'eke.publications',
    'eke.site',
    'eke.study',
    'eke.biomarker',
    'eke.committees',
    'eke.ecas',
    'eke.review',
    'eke.specimens',
)
EXTENSION_PROFILES = ('edrnsite.policy:default',)

def install(context, reinstall=False):
    quickInstaller = getToolByName(context, 'portal_quickinstaller')
    setupTool = getToolByName(context, 'portal_setup')
    for product in PRODUCT_DEPENDENCIES:
        if reinstall and quickInstaller.isProductInstalled(product):
            quickInstaller.reinstallProducts(product)
            transaction.savepoint()
        elif not quickInstaller.isProductInstalled(product):
            quickInstaller.installProduct(product)
            transaction.savepoint()
    for extensionID in EXTENSION_PROFILES:
        setupTool.runAllImportStepsFromProfile('profile-%s' % extensionID, purge_old=False)
        productName = extensionID.split(':')[0]
        quickInstaller.notifyInstalled(productName)
        transaction.savepoint()
    

