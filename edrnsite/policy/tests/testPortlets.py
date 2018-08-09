# encoding: utf-8
# Copyright 2008–2012 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

'''Tests for the EDRN site's portlets.
'''

import unittest
from edrnsite.policy.testing import EDRNSITE_POLICY_INTEGRATION_TESTING
from zope.component import getUtility, getMultiAdapter
from plone.portlets.interfaces import IPortletManager, IPortletAssignmentMapping

class PortletsTest(unittest.TestCase):
    '''Unit tests of the porlets for the EDRN site policy.'''
    layer = EDRNSITE_POLICY_INTEGRATION_TESTING
    def setUp(self):
        super(PortletsTest, self).setUp()
        self.portal = self.layer['portal']
    def testLeftPortlets(self):
        # At the root of the site, the left column should have the review list and quick links
        left = getUtility(IPortletManager, u'plone.leftcolumn')
        mgr = getMultiAdapter((self.portal, left), IPortletAssignmentMapping)
        self.assertEquals(2, len(mgr))
        self.assertEquals(['review-list', 'edrn-quick-links'], mgr.keys())

    def testRightPortlets(self):
        # At the root of the site, the right column should have a search box and announcements
        right = getUtility(IPortletManager, u'plone.rightcolumn')
        mgr = getMultiAdapter((self.portal, right), IPortletAssignmentMapping)
        self.assertEquals(2, len(mgr))
        self.assertEquals(['search','DMCCRSS-announcements'], mgr.keys())

def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
