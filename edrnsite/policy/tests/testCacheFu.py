# encoding: utf-8
# Copyright 2008 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

'''Tests for the CacheFu configuration of the EDRN Site policy.
'''

import unittest, threading
from edrnsite.policy.tests.base import EDRNSitePolicyTestCase

class TestCacheFu(EDRNSitePolicyTestCase):
    '''Unit tests the CacheFu configuration of the EDRN site policy.'''
    def setUp(self):
        super(TestCacheFu, self).setUp()
        self.cacheTool = getattr(self.portal, 'portal_cache_settings', None)
        if self.cacheTool:
            for i in self.cacheTool.objectIds():
                if i.startswith('default-cache-policy'):
                    self.rules = self.cacheTool[i]['rules']
                    break
    def testCacheFuSetup(self):
        '''Ensure CacheFu is installed and enabled.'''
        if not self.cacheTool: return
        self.failUnless(self.cacheTool.enabled)
        self.failUnless(self.cacheTool.activePolicyId.startswith('default-cache-policy'))
        self.assertEquals(u'no-rewrite', self.cacheTool.proxyPurgeConfig)
    def testContainerCaching(self):
        '''Check if our container types are marked for caching.'''
        if not self.cacheTool: return
        contentTypes = self.rules['plone-containers'].getContentTypes()
        for i in (
            'Biomarker Folder', 'Biomarker Panel', 'Funding Folder', 'Knowledge Folder', 'Publication Folder', 'Site Folder',
            'Study Folder', 'Committee Folder'
        ):
            self.failUnless(i in contentTypes)
    def testContentCaching(self):
        '''Check if our leaf content types are marked for caching.'''
        if not self.cacheTool: return
        contentTypes = self.rules['plone-content-types'].getContentTypes()
        for i in (
            'Announcement', 'Body System', 'Disease', 'Elemental Biomarker', 'Funding Opportunity', 'Knowledge Object',
            'Protocol', 'Publication', 'Site', 'Committee'
        ):
            self.failUnless(i in contentTypes)
    def tearDown(self):
        # Work around CacheFu bug: purge thread is left running as non-daemon thread.
        # This prevents unit test process from ever terminating.
        for i in threading.enumerate():
            if i.getName() == 'PurgeThread for http://edrn.nci.nih.gov:80':
                i.stopping = True

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCacheFu))
    return suite
    
