# encoding: utf-8
# Copyright 2010 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

'''Tests for the EDRN site's content rules.
'''

import unittest
from edrnsite.policy.tests.base import EDRNSitePolicyTestCase
from zope.component import getUtility
from plone.contentrules.engine.interfaces import IRuleStorage, IRuleAssignmentManager
from plone.app.contentrules.actions.mail import IMailAction

# Notification address for all content rules:
_email = u'heather.kincaid@jpl.nasa.gov'

# Top-level folders that should have content rules:
_foldersToCheck = (
    'about-edrn',
    'admin',
    'advocates',
    'colops',
    'committees',
    'docs',
    'funding-opportunities',
    'researchers',
    'resources',
)

# Rules we want installed in top-level folders and the PloneSite object:
_rulesToCheck = ('edrn-add-event', 'edrn-mod-event', 'edrn-del-event', 'edrn-pub-event')

class TestContentRuleEvents(EDRNSitePolicyTestCase):
    '''Unit tests of the setup of content rule events for the EDRN site policy'''
    def setUp(self):
        super(TestContentRuleEvents, self).setUp()
        self.ruleStorage = getUtility(IRuleStorage)
    def testActiveRules(self):
        '''Ensure content rules are enabled globally'''
        self.failUnless(self.ruleStorage.active)
    def testAddEvent(self):
        e = self.ruleStorage['edrn-add-event']
        self.assertEquals(u'EDRN Event: Item Added', e.title)
        self.assertEquals(u'Event triggered when an item is added (newly created or pasted) to a container.', e.description)
        self.assertEquals(0, len(e.conditions))
        self.assertEquals(1, len(e.actions))
        a = e.actions[0]
        self.failUnless(IMailAction.providedBy(a))
        self.assertEquals(u'EDRN Portal: new item added', a.subject)
        self.assertEquals(_email, a.recipients)
        self.failUnless(u'A new item has been added' in a.message)
    def testModifiedEvent(self):
        e = self.ruleStorage['edrn-mod-event']
        self.assertEquals(u'EDRN Event: Item Modified', e.title)
        self.assertEquals(u'Event triggered when an item is modified (edited or altered).', e.description)
        self.assertEquals(0, len(e.conditions))
        self.assertEquals(1, len(e.actions))
        a = e.actions[0]
        self.failUnless(IMailAction.providedBy(a))
        self.assertEquals(u'EDRN Portal: item modified', a.subject)
        self.assertEquals(_email, a.recipients)
        self.failUnless(u'has been modified' in a.message)
    def testDeletedEvent(self):
        e = self.ruleStorage['edrn-del-event']
        self.assertEquals(u'EDRN Event: Item Deleted', e.title)
        self.assertEquals(u'Event triggered when an item is removed (moved or deleted) from a container.', e.description)
        self.assertEquals(0, len(e.conditions))
        self.assertEquals(1, len(e.actions))
        a = e.actions[0]
        self.failUnless(IMailAction.providedBy(a))
        self.assertEquals(u'EDRN Portal: item deleted', a.subject)
        self.assertEquals(_email, a.recipients)
        self.failUnless(u'has been deleted' in a.message)
    def testStateChangeEvent(self):
        e = self.ruleStorage['edrn-pub-event']
        self.assertEquals(u'EDRN Event: Publication State Changed', e.title)
        self.assertEquals(u'Event triggered when an item has its publication state adjusted.', e.description)
        self.assertEquals(0, len(e.conditions))
        self.assertEquals(1, len(e.actions))
        a = e.actions[0]
        self.failUnless(IMailAction.providedBy(a))
        self.assertEquals(u'EDRN Portal: publication state changed', a.subject)
        self.assertEquals(_email, a.recipients)
        self.failUnless(u'had its publication state changed' in a.message)

class TestContentRuleInstantiation(EDRNSitePolicyTestCase):
    '''Test installation of content rules into various folders within the EDRN portal'''
    def testRootContentRules(self):
        '''Ensure content rules are installed at the top (root) of the portal'''
        # At the root, all four of our rules should be instantiated and enabled, however none should bubble down.
        rules = IRuleAssignmentManager(self.portal)
        for i in _rulesToCheck:
            rule = rules[i]
            self.failUnless(rule.enabled)
            self.failIf(rule.bubbles)
    def testFolderContentRules(self):
        '''Make certain content rules are installed in select folders'''
        # For all non-knowledge folders (that is, content NOT ingested from RDF), we want all four events
        # instantiated, enabled, *and* for their effects to bubble down into their subfolders.
        for f in _foldersToCheck:
            folder = self.portal[f]
            rules = IRuleAssignmentManager(folder)
            for i in _rulesToCheck:
                self.failUnless(i in rules, 'Content rule "%s" missing from folder "%s"' % (i, f))
                rule = rules[i]
                self.failUnless(rule.enabled)
                self.failUnless(rule.bubbles)
            
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestContentRuleEvents))
    suite.addTest(unittest.makeSuite(TestContentRuleInstantiation))
    return suite
    
