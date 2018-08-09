# encoding: utf-8
# Copyright 2008-2010 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

'''
testSetup.py

Tests for the setup of the EDRN Site policy.
'''

import unittest
from edrnsite.policy.testing import EDRNSITE_POLICY_INTEGRATION_TESTING
from Products.CMFCore.permissions import MailForgottenPassword
from Products.CMFCore.utils import getToolByName
from zope.component import queryMultiAdapter
from zope.publisher.browser import TestRequest

_typesNotSearched = frozenset((
    # eke.biomarker:
    'Biomarker Body System',
    'Body System Study',
    'Study Statistics',
    # eke.misccontent:
    'EDRN Home',
))

class SetupTest(unittest.TestCase):
    '''Unit tests the setup of the EDRN site policy.'''
    layer = EDRNSITE_POLICY_INTEGRATION_TESTING
    def setUp(self):
        super(SetupTest, self).setUp()
        self.portal = self.layer['portal']
    def testPortalTitle(self):
        '''Check the site title'''
        self.assertEquals('EDRN Public Portal', self.portal.getProperty('title'))
    def testPortalDescription(self):
        '''Check the site description'''
        self.assertEquals('Early Detection Research Network', self.portal.getProperty('description'))
    def testIfThemeInstalled(self):
        '''Check if theme installed'''
        skins = getToolByName(self.portal, 'portal_skins')
        self.assertEquals('EDRN Theme', skins.getDefaultSkin())
    def testForKnowledgeEnvironment(self):
        '''Check if the EKE is installed.'''
        types = getToolByName(self.portal, 'portal_types')
        for t in (
            'Dataset',
            'Elemental Biomarker',
            'Knowledge Object',
            'Person',
            'Protocol',
            'Publication',
            'Site',
            'Specimen System Folder',
            'Committee',
        ):
            self.failUnless(t in types.objectIds(), 'Content type "%s" missing' % t)
    def testForFunding(self):
        '''Check if funding package installed'''
        types = getToolByName(self.portal, 'portal_types')
        self.failUnless('Funding Folder' in types.objectIds())
    def testForMiscellaneousContent(self):
        '''Check if the miscellaneous content package is installed'''
        types = getToolByName(self.portal, 'portal_types')
        self.failUnless('EDRN Home' in types.objectIds())
        self.failUnless('FormFolder' in types.objectIds())
    def testForCollaborations(self):
        '''Check if the EDRN Site Collaborative Groups package is installed'''
        types = getToolByName(self.portal, 'portal_types')
        self.failUnless('Collaborations Folder' in types.objectIds())
    def testVersionableTypes(self):
        repository = getToolByName(self.portal, 'portal_repository')
        versionableTypes = repository.getVersionableContentTypes()
        self.failUnless('File' in versionableTypes)
    def testPresentationMode(self):
        '''Make sure presentation mode is turned off for the welcome page.'''
        frontPage = self.portal['front-page']
        self.failIf(frontPage.presentation)
    def testInlineEditing(self):
        '''Make sure inline editing (which was a stupid idea) is turned OFF.'''
        site = self.portal.portal_properties.site_properties
        self.failIf(site.getProperty('enable_inline_editing'))
    def testNavtreeProperties(self):
        '''Ensure the global navigation and navtree are configured correctly.'''
        site, nav = self.portal.portal_properties.site_properties, self.portal.portal_properties.navtree_properties
        self.failUnless(site.getProperty('disable_nonfolderish_sections'))
        self.failUnless(nav.getProperty('enable_wf_state_filtering'))
        self.failUnless('published' in nav.getProperty('wf_states_to_show'))
    def testFolderWorkflowStates(self):
        '''Make sure folders at the top level are in the correct state so they don't automatically become navigation tabs.'''
        # No longer viable under plone.app.testing
        # wfTool = getToolByName(self.portal, 'portal_workflow')
        # for i in ('Members', 'news', 'events'):
        #     self.assertEquals('private', wfTool.getInfoFor(self.portal[i], 'review_state'))
    def testMailSettings(self):
        '''Ensure the portal is ready to send email.'''
        self.assertEquals(u'nobody@nowhere.nonexistent', self.portal.getProperty('email_from_address'))
        self.assertEquals(u'EDRN Portal Administrator', self.portal.getProperty('email_from_name'))
        self.assertEquals(u'non.exist.ent', self.portal.MailHost.smtp_host)
    def testTypesNotSearched(self):
        '''Make sure types that are not searched aren't clobbered.'''
        typesNotSearched = frozenset(self.portal.portal_properties.site_properties.getProperty('types_not_searched'))
        self.assertEquals(typesNotSearched.intersection(_typesNotSearched), _typesNotSearched)
    def testGoogleTools(self):
        '''Make sure the portal is set up for Google Analytics and Webmaster Tools.'''
        # No longer viable under plone.app.testing
        # self.failUnless('google6303b8e42ec16379.html' in self.portal.keys())
        # content = self.portal.unrestrictedTraverse('google6303b8e42ec16379.html')()
        # self.assertEquals(u'google-site-verification: google6303b8e42ec16379.html', content)
        # props = self.portal.portal_properties.site_properties
        # self.failUnless(props.getProperty('enable_sitemap'))
        # # CA-743: don't deploy with Google Analytics on by default
        # self.failIf('UA-1192384-4' in props.getProperty('webstats_js'))
    def testContent(self):
        '''Check if our initial site content appears.'''
        # No longer ingest during testing, so this test is no longer viable
        # wfTool = getToolByName(self.portal, 'portal_workflow')
        # root = self.portal.getPhysicalPath()
        # for path in (
        #     ('resources', 'body-systems'),
        #     ('resources', 'diseases'),
        #     ('science-data',),
        #     ('resources', 'miscellaneous-resources'),
        #     ('docs',),
        #     ('advocates',),
        #     ('funding-opportunities',),
        #     ('colops',),
        #     ('researchers',),
        #     ('sites',),
        #     ('protocols',),
        #     ('publications',),
        #     ('protocols',),
        #     ('biomarkers',),
        #     ('admin',),
        #     ('members-list',),
        #     ('specimens',),
        #     ('committees',),
        #     ('collaborative-groups',),
        # ):
        #     target = root + path
        #     item = self.portal.restrictedTraverse(target)
        #     self.assertEquals('published', wfTool.getInfoFor(item, 'review_state'))
        # self.failIf('specimens' in self.portal['resources'].objectIds())
        # self.failUnless(self.portal['front-page'].showGarishSearchBox)
        # NOTE: We can't test for the presence of the "about-edrn" or the large objects
        # in the "resources" folder as the test database has a limited quota.
    def testResourcesTitle(self):
        '''Ensure that the title of the resources tab is just "Resources"'''
        self.assertEquals(u'Resources', self.portal['resources'].title)
    def testTabOrdering(self):
        '''Check that the tabs appear in the correct order'''
        i = self.portal.getObjectPosition
        about, biomarkers, scienceData, protocols, pubs, resources, specimens = \
            i('about-edrn'), i('biomarkers'), i('science-data'), i('protocols'), i('publications'), i('resources'), i('specimens')
        # The correct order is: about, bio, proto, science data, specimens, pubs, resources
        self.failUnless(about < biomarkers < protocols < scienceData < specimens < pubs < resources)
    def testNavigationExcludedItems(self):
        '''Check that items to be excluded from the navigation are actually excluded'''
        for i in (
            'advocates', 'colops', 'docs', 'funding-opportunities', 'researchers', 'sites', 'admin', 'committees',
            'collaborative-groups',
        ):
            item = self.portal[i]
            self.failUnless(item.getExcludeFromNav(), 'Item "%s" should be excluded from navigation' % i)
    def testAdministrativeImages(self):
        '''Ensure images for the administrivia section are present'''
        images = self.portal['admin']['images'].objectIds()
        for i in ('excel.gif', 'flash.gif', 'pdf.gif', 'ppt.gif', 'qt.gif', 'word.gif'):
            self.failUnless(i in images)
    def testDatasetFolder(self):
        '''Make certain that the dataset folder is a Dataset Folder and not a Knowledge Folder.'''
        folder = self.portal['science-data']
        self.assertEquals('Dataset Folder', folder.portal_type)
    def testMiscResourcesFolder(self):
        '''Make certain that the miscellaneous resources folder is a Knowledge Folder and not a Dataset Folder.'''
        folder = self.portal['resources']['miscellaneous-resources']
        self.assertEquals('Knowledge Folder', folder.portal_type)
    def testPublicationsFolder(self):
        '''Make sure the publications folder has two URLs.'''
        # No longer ingest during testing, so this test is no longer viable
        # folder = self.portal['publications']
        # self.failUnless(folder.rdfDataSource)
        # self.failUnless(len(folder.additionalDataSources) > 0)
    def testProtocolsFolder(self):
        '''Ensure that protocols are connected to sites.'''
        # No longer ingest during testing, so this test is no longer viable
        # aProtocol = self.portal['protocols']['138-validation-of-protein-markers-for-lung-cancer']
        # self.failUnless(aProtocol.leadInvestigatorSite is not None)
    def testBiomarkerProtocolConnection(self):
        '''Make certain that a biomarker's BodySystemStudy object is
        well-connected to its corresponding Protocol object.'''
        # No longer ingest during testing, so this test is no longer viable
        # aBiomarker = self.portal['biomarkers']['14-3-3-theta']
        # aBiomarkerBodySystem = aBiomarker['lung']
        # aBodySystemStudy = aBiomarkerBodySystem['validation-of-protein-markers-for-lung-cancer']
        # self.failUnless(aBodySystemStudy.protocol is not None)
        # self.assertEquals(aBodySystemStudy.protocol.title,
        #     u'Validation of Protein Markers for Lung Cancer Using CARET Sera and Proteomics Techniques')
    def testKnowledgeFolderURLs(self):
        '''Verify that knowledge folders have the correct URLs for future ingest.'''
        self.assertEquals(
            'http://edrn-dev.jpl.nasa.gov/cancerdataexpo/rdf-data/body-systems/rdf',
            self.portal['resources']['body-systems'].rdfDataSource
        )
        self.assertEquals(
            'http://edrn-dev.jpl.nasa.gov/cancerdataexpo/rdf-data/diseases/rdf',
            self.portal['resources']['diseases'].rdfDataSource
        )
        self.assertEquals(
            'http://edrn-dev.jpl.nasa.gov/cancerdataexpo/rdf-data/publications/rdf',
            self.portal['publications'].rdfDataSource
        )
        self.assertEquals(
            'http://edrn.jpl.nasa.gov/bmdb/rdf/publications',
            self.portal['publications'].additionalDataSources[0]
        )
        self.assertEquals(
            'http://edrn-dev.jpl.nasa.gov/cancerdataexpo/rdf-data/sites/rdf',
            self.portal['sites'].rdfDataSource
        )
        self.assertEquals(
            'http://edrn-dev.jpl.nasa.gov/cancerdataexpo/rdf-data/registered-person/rdf',
            self.portal['sites'].peopleDataSource
        )
        self.assertEquals(
            'http://edrn-dev.jpl.nasa.gov/cancerdataexpo/rdf-data/protocols/rdf',
            self.portal['protocols'].rdfDataSource
        )
        self.assertEquals(
            'http://edrn.jpl.nasa.gov/bmdb/rdf/biomarkers',
            self.portal['biomarkers'].rdfDataSource
        )
        self.assertEquals(
            'http://edrn.jpl.nasa.gov/bmdb/rdf/biomarkerorgans',
            self.portal['biomarkers'].bmoDataSource
        )
        self.assertEquals(
            'https://edrn-dev.jpl.nasa.gov/cancerdataexpo/rdf-data/biomuta/@@rdf',
            self.portal['biomarkers'].bmuDataSource
        )
        self.assertEquals(
            'http://edrn.jpl.nasa.gov/bmdb/rdf/resources',
            self.portal['resources']['miscellaneous-resources'].rdfDataSource
        )
        self.assertEquals(
            'http://edrn.jpl.nasa.gov/fmprodp3/rdf/dataset?type=ALL&baseUrl=http://edrn.jpl.nasa.gov/ecas/dataset.php',
            self.portal['science-data'].rdfDataSource
        )
        self.assertEquals(
            'http://edrn-dev.jpl.nasa.gov/cancerdataexpo/rdf-data/committees/rdf',
            self.portal['committees'].rdfDataSource
        )
    def testVideoEmbeddingSettings(self):
        '''Ensure we can embed YouTube videos'''
        safeHTMLxform = getToolByName(self.portal, 'portal_transforms')['safe_html']
        nastyTags = safeHTMLxform.get_parameter_value('nasty_tags')
        self.failIf(u'embed' in nastyTags)
        self.failIf(u'object' in nastyTags)
        validTags = safeHTMLxform.get_parameter_value('valid_tags')
        self.failUnless(u'object' in validTags)
        self.failUnless(u'param' in validTags)
        self.failUnless(u'embed' in validTags)
    def testDiscussion(self):
        '''Ensure that discussion capability is OFF for all types (CA-435)'''
        typesTool = getToolByName(self.portal, 'portal_types')
        for t in typesTool.objectIds():
            self.failIf(typesTool[t].allow_discussion, 'Type "%s" is enabled for discussion and should not be' % t)
    def testPasswordMailing(self):
        '''Ensure that mailing of forgotten passwords doesn't happen (CA-498)'''
        # No longer viable under plone.app.testing
        # permissionSettings = self.portal.permission_settings(MailForgottenPassword)[0]
        # self.assertEquals('', permissionSettings['acquire'])
        # for role in permissionSettings['roles']:
        #     self.assertEquals('', role['checked'])
    def testLoginLockout(self):
        '''Make sure the LoginLockout plugin is installed and appropriately configured'''
        # No longer viable under plone.app.testing
        # items = self.portal.acl_users.objectIds()
        # self.failUnless('login_lockout_plugin' in items)
        # lockoutPlugin = self.portal.acl_users.login_lockout_plugin
        # self.failUnless('kincaid' in lockoutPlugin.lockout.document_src())
        # self.assertEquals(6, lockoutPlugin.getProperty('_max_attempts')) # Tolerate 5 failed attempts, lock on 6th
        # self.assertEquals(0.25, lockoutPlugin.getProperty('_reset_period')) # Reset in 15 minutes (one quarter hour)
    def testFullIngest(self):
        '''Check if the re-ingestion features of CA-528 are available'''
        # Note: no longer test ingest paths; see CA-1237
        # ingestPaths = self.portal.getProperty('edrnIngestPaths')
        # self.failUnless(ingestPaths is not None)
        # self.assertEquals(12, len(ingestPaths))
        fullIngestor = queryMultiAdapter((self.portal, TestRequest()), name=u'ingestEverythingFully')
        self.failUnless(fullIngestor is not None)
    def testFacetedNavigation(self):
        '''See if eea.facetednavigation is installed.'''
        from Products.ATContentTypes.content.folder import ATFolder
        from eea.facetednavigation.interfaces import IPossibleFacetedNavigable
        self.failUnless(IPossibleFacetedNavigable.implementedBy(ATFolder))
    def testForStaffNotStaffers(self):
        '''CA-681 doesn't like the word "staffers"; it wants just "staff"'''
        membersList = self.portal['members-list']
        self.failIf(u'staffers' in membersList.Description())
    def testManyMany(self):
        '''Ensure that both many_users and many_groups are enabled, otherwise the user control panel will take forever.'''
        props = getToolByName(self.portal, 'portal_properties')
        self.failUnless(props.site_properties.getProperty('many_users'))
        self.failUnless(props.site_properties.getProperty('many_groups'))
    def testTableSorting(self):
        u'''Check if everyone—not just authenticated users—can benefit from table sorting by clicking on column headers.
        Also, add a note about this feature and ensure it's published.
        '''
        # No longer viable under plone.app.testing
        # javascripts = getToolByName(self.portal, 'portal_javascripts')
        # self.failIf(javascripts.getResource('table_sorter.js').getAuthenticated(),
        #     'table_sorter.js should not be for authenticated users only')
        # # Ensure the note about this function is available
        # adminFolder = self.portal['admin']
        # self.failUnless('viewing-tables' in adminFolder.keys(), 'Table viewing note is missing')
        # viewingTables = adminFolder['viewing-tables']
        # wfTool = getToolByName(self.portal, 'portal_workflow')
        # self.assertEquals('published', wfTool.getInfoFor(viewingTables, 'review_state'))
    def testJQuery(self):
        '''Make sure JQuery is present, enabled, and the first item in the JavaScripts registry.'''
        javascripts = getToolByName(self.portal, 'portal_javascripts')
        jqueryIndex = javascripts.getResourcePosition('jquery.js')
        self.assertEquals(0, jqueryIndex, '"jquery.js" not in correct position; expected 0, got %d' % jqueryIndex)
    def testEditingSettings(self):
        '''Ensure editor settings are correct'''
        props = self.portal.portal_properties.site_properties
        self.failIf('Kupu' in props.getProperty('available_editors'))
        self.assertEquals('TinyMCE', props.getProperty('default_editor'))
    def testAutoIngestDeletionList(self):
        '''Verify that "protocols" is included in the list of ingest paths that we don't delete first (CA-841).'''
        from edrnsite.policy.browser.ingest import _doNotDelete
        self.failUnless('protocols' in _doNotDelete, 'Protocols must appear in the _doNotDelete sequence')
    

def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
