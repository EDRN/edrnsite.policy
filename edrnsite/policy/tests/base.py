# encoding: utf-8
# Copyright 2009-2010 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

'''
Testing base code.
'''

from Products.Five import fiveconfigure
from Products.Five import zcml
from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import onsetup
from Testing import ZopeTestCase as ztc

# Traditional Products we have to load manually for test cases:
ztc.installProduct('CacheSetup')
ztc.installProduct('LoginLockout')

@onsetup
def setupEDRNSitePolicy():
    '''Set up additional products required for the EDRN site policy.'''
    fiveconfigure.debug_mode = True
    import edrnsite.policy
    zcml.load_config('configure.zcml', edrnsite.policy)
    fiveconfigure.debug_mode = False
    ztc.installPackage('p4a.subtyper')
    ztc.installPackage('eea.facetednavigation')
    ztc.installPackage('plone.app.ldap')
    ztc.installPackage('eke.specimens')
    ztc.installPackage('eke.review')
    ztc.installPackage('eke.committees')
    ztc.installPackage('eke.ecas')
    ztc.installPackage('eke.biomarker')
    ztc.installPackage('eke.study')
    ztc.installPackage('eke.site')
    ztc.installPackage('eke.knowledge')
    ztc.installPackage('eke.publications')
    ztc.installPackage('edrnsite.portlets')
    ztc.installPackage('edrnsite.search')
    ztc.installPackage('edrnsite.funding')
    ztc.installPackage('edrnsite.misccontent')
    ztc.installPackage('edrn.theme')
    ztc.installPackage('edrnsite.policy')
    
setupEDRNSitePolicy()
ptc.setupPloneSite(products=['edrnsite.policy'])

class EDRNSitePolicyTestCase(ptc.PloneTestCase):
    '''Base for tests in this package.'''
    pass
    
class EDRNSitePolicyFunctionalTestCase(ptc.FunctionalTestCase):
    '''Base class for functional (doc-)tests.'''
    pass
    
