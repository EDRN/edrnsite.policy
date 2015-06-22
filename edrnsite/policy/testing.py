# encoding: utf-8
# Copyright 2012 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

from plone.app.testing import PloneSandboxLayer, PLONE_FIXTURE, IntegrationTesting, FunctionalTesting
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import quickInstallProduct
from plone.testing import z2
from Products.CMFCore.utils import getToolByName
import sys

_testDeps = (
    'plone.app.ldap',
    'edrn.theme',
#    'edrnsite.content',
    'edrnsite.portlets',
    'edrnsite.funding',
    'edrnsite.misccontent',
    'edrnsite.collaborations',
    'edrnsite.vanity',
    'eke.knowledge',
    'eke.publications',
    'eke.site',
    'eke.study',
    'eke.biomarker',
    'eke.committees',
    'eke.ecas',
    'eke.review',
    'eke.specimens',
    'eke.secretome',
    'eea.facetednavigation',
)

class EDRNSitePolicy(PloneSandboxLayer):
    defaultBases = (PLONE_FIXTURE,)
    def setUpZope(self, app, configurationContext):
        for dep in _testDeps:
            __import__(dep)
            self.loadZCML(package=sys.modules[dep])
            z2.installProduct(app, dep)
        import edrnsite.policy
        self.loadZCML(package=edrnsite.policy)
        z2.installProduct(app, 'edrnsite.policy')
    def setUpPloneSite(self, portal):
        self.applyProfile(portal, 'edrnsite.policy:default')
        setRoles(portal, TEST_USER_ID, ['Manager'])
        wfTool = getToolByName(portal, 'portal_workflow')
        wfTool.setDefaultChain('plone_workflow')
        quickInstallProduct(portal, 'plone.app.ldap')
    def tearDownZope(self, app):
        z2.uninstallProduct(app, 'edrnsite.policy')


EDRNSITE_POLICY_FIXTURE = EDRNSitePolicy()
EDRNSITE_POLICY_INTEGRATION_TESTING = IntegrationTesting(bases=(EDRNSITE_POLICY_FIXTURE,), name='EDRNSitePolicy:Integration')
EDRNSITE_POLICY_FUNCTIONAL_TESTING = FunctionalTesting(bases=(EDRNSITE_POLICY_FIXTURE,), name='EDRNSitePolicy:Functional')
