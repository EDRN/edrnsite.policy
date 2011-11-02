# encoding: utf-8
# Copyright 2010-2011 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

from plone.app.viewletmanager.interfaces import IViewletSettingsStorage
from plone.i18n.normalizer.interfaces import IIDNormalizer
from Products.CMFCore.utils import getToolByName
from setuphandlers import enableEmbeddableVideos, createCommitteesFolder, createCollaborationsFolder, _doPublish
from setuphandlers import orderFolderTabs, createMembersListSearchPage, createSpecimensPage
from setuphandlers import addTableSortingNote
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.publisher.browser import TestRequest
import transaction, re

# Dependent packages in profile 0
_dependencies0 = (
    'Products.CacheSetup',
    'LoginLockout',
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
    'eke.ecas',
    'eke.review',
)
# Dependent packages in profile 4
_dependencies4 = (
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
    'eke.ecas',
    'eke.review',
    'eke.specimens',
)

# New packages in profile 0 (but never made it into 3.6 which is at NCI)
_newPackages0 = (
    'eke.committees',
)
# So we'll get it this time:
_newPackages4 = (
    'eke.committees',
    # As well as this new one:
    'edrnsite.collaborations',
)

# Old site ID format
_oldSiteIDRegexp = re.compile(r'^([a-z-]+)-([0-9]+)$')

def _getPortal(context):
    return getToolByName(context, 'portal_url').getPortalObject()

def _setPurging(portal, mode):
    cacheTool = getToolByName(portal, 'portal_cache_settings')
    cacheTool.setEnabled(mode)
    if mode:
        cacheTool.setDomains(['http://edrn.nci.nih.gov:80'])
    else:
        cacheTool.setDomains([])

def setAutoIngestProperties(portal):
    if not portal.hasProperty('edrnIngestPaths'):
        ingestPaths = (
            'resources/body-systems',
            'resources/diseases',
            'resources/miscellaneous-resources',
            'protocols',
            'sites',
            'publications',
            'biomarkers',
            'science-data',
            'protocols',
            'science-data',
            'biomarkers',
            'committees',
        )
        portal.manage_addProperty('edrnIngestPaths', ingestPaths, 'lines')

def installNewPackages(portal, packageList):
    quickInstaller = getToolByName(portal, 'portal_quickinstaller')
    for package in packageList:
        if quickInstaller.isProductInstalled(package):
            continue
        else:
            quickInstaller.installProduct(package)
            transaction.savepoint()

def fixSiteIDs(portal):
    if 'sites' not in portal.objectIds(): return
    sites = portal['sites']
    oldIDs, newIDs, needIDs = [], [], []
    for objID in sites.objectIds():
        m = _oldSiteIDRegexp.match(objID)
        if m:
            newID = '%s-%s' % (m.group(2), m.group(1))
            newIDs.append(newID)
            oldIDs.append(objID)
        else:
            needIDs.append(objID)
    assert len(oldIDs) == len(newIDs), 'Mismatch between old site object IDs and new site object IDs'
    if oldIDs and newIDs:
        sites.manage_renameObjects(oldIDs, newIDs)
    if needIDs:
        normalizer = getUtility(IIDNormalizer).normalize
        for objID in needIDs:
            site = sites[objID]
            newID = normalizer('%s %s' % (site.siteID, site.title))
            sites.manage_renameObject(objID, newID)

def updateGoogleSiteVerification(portal):
    if 'google6303b8e42ec16379.html' not in portal.objectIds(): return
    siteVerificationPage = portal['google6303b8e42ec16379.html']
    siteVerificationPage.write(u"<tal:content replace='string:google-site-verification: google6303b8e42ec16379.html'/>")

def removeGoogleAnalytics(portal):
    '''For CA-743, disable Google Analytics since NCI doesn't like long term cookies.'''
    props = getToolByName(portal, 'portal_properties').site_properties
    props.manage_changeProperties(webstats_js=u'')

def upgrade0to1(setupTool):
    portal = _getPortal(setupTool)
    _setPurging(portal, False)
    catalog = getToolByName(portal, 'portal_catalog')
    catalog.clearFindAndRebuild()
    qi = getToolByName(portal, 'portal_quickinstaller')
    qi.reinstallProducts(_dependencies0)
    for product in _dependencies0:
        qi.upgradeProduct(product)
        transaction.commit()
    qi.installProducts(['eea.facetednavigation', 'eke.specimens'])
    setAutoIngestProperties(portal)
    orderFolderTabs(portal)
    createMembersListSearchPage(portal)
    enableEmbeddableVideos(portal)
    installNewPackages(portal, _newPackages0)
    createCommitteesFolder(portal)
    fixSiteIDs(portal)
    updateGoogleSiteVerification(portal)
    removeGoogleAnalytics(portal)
    catalog.clearFindAndRebuild()
    _setPurging(portal, True)

def nukeCustomizedLoginForm(portal):
    '''The login_form was customized TTW at NCI to add a long and boring disclaimer,
    as well as forgotten and change password links that link to the awful DMCC.
    In this profile, the modified login_form is part of edrn.theme and we
    can get rid of the one in custom.'''
    skinsTool = getToolByName(portal, 'portal_skins')
    if 'login_form' in skinsTool.custom.keys():
        skinsTool.custom.manage_delObjects(['login_form'])

def removeExtraViewlets(portal):
    storage = getUtility(IViewletSettingsStorage)
    skinname = portal.getCurrentSkinName()
    for manager, viewlet in (
        ('plone.contentviews', 'edrn.path_bar'),
        ('plone.portalfooter', 'plone.site_actions'),
        ('plone.portaltop', 'plone.personal_bar'),
    ):
        hidden = storage.getHidden(manager, skinname)
        if viewlet not in hidden:
            hidden = hidden + (viewlet,)
            storage.setHidden(manager, skinname, hidden)
    
def nukeCustomizedCSS(portal):
    '''The CSS was customized TTW at NCI because of some IE7 issue.  It turns out
    it was totally unrelated to the CSS customization.  So in this profile, we
    get rid of it.'''
    skinsTool = getToolByName(portal, 'portal_skins')
    if 'ploneCustom.css' in skinsTool.custom.keys():
        skinsTool.custom.manage_delObjects(['ploneCustom.css'])

def nukeCustomizedViews(portal):
    '''The logo viewlet was customized TTW at NCI because of some IE7 issue.  We've
    since brought that modified HTML into edrn.theme, so we can now get rid
    of the view customization.
    '''
    viewCustomizationTool = getToolByName(portal, 'portal_view_customizations')
    if 'zope.interface.interface-edrn.logo' in viewCustomizationTool.keys():
        viewCustomizationTool.manage_delObjects(['zope.interface.interface-edrn.logo'])

def ingestCommittees(portal):
    if 'committees' not in portal.objectIds(): return
    committees = portal['committees']
    ingestor = getMultiAdapter((committees, TestRequest()), name=u'ingest')
    ingestor.render = False
    try:
        ingestor()
    except:
        pass
    _doPublish(committees, getToolByName(portal, 'portal_workflow'))

def resetIngestPaths(portal):
    if portal.hasProperty('edrnIngestPaths'):
        portal.manage_delProperties(['edrnIngestPaths'])
    setAutoIngestProperties(portal)

def upgrade1to4(setupTool):
    portal = _getPortal(setupTool)
    
    # Disable annoying link integrity checking
    propTool = getToolByName(portal, 'portal_properties')
    origLinkIntegrityMode = propTool.site_properties.getProperty('enable_link_integrity_checks', True)
    propTool.site_properties.manage_changeProperties(enable_link_integrity_checks=False)
    
    # I do not comprehend why we still have old-style site IDs.  Kill 'em all
    # and let re-ingest bring 'em back
    portal.sites.manage_delObjects(portal.sites.keys())
    
    # Kill the old specimens tab
    if 'specimens' in portal.keys():
        portal.manage_delObjects('specimens')
    
    # Recatalog
    catalog = getToolByName(portal, 'portal_catalog')
    catalog.clearFindAndRebuild()
    
    # Reinstall
    qi = getToolByName(portal, 'portal_quickinstaller')
    qi.reinstallProducts(_dependencies4)
    for product in _dependencies4:
        qi.upgradeProduct(product)
        transaction.commit()
    qi.installProducts(['eea.facetednavigation', 'eke.specimens'])
    installNewPackages(portal, _newPackages4)
    transaction.commit()
 
    # FIXME: OK, the above allegedly did a reinstall of eke.publications which was a profile 0
    # to profile 4. However, tracing through, I found it was already at profile 4! WTF?!
    # Until I can figure that out, I'm manually calling eke.publications's upgrade step:
    from eke.publications.upgrades import setUpFacetedNavigation
    setUpFacetedNavigation(setupTool)
    # Same with specimens:
    from eke.specimens.upgrades import addSampleSpecimenSets, addFacetedSearch, updateDiagnosisIndex
    addSampleSpecimenSets(setupTool)
    addFacetedSearch(setupTool)
    updateDiagnosisIndex(setupTool)
   
    # Remove customizations that made it into software
    nukeCustomizedLoginForm(portal)
    nukeCustomizedCSS(portal)
    nukeCustomizedViews(portal)
    removeExtraViewlets(portal)
    transaction.commit()
    
    # Recreate faceted pages
    createMembersListSearchPage(portal)
    transaction.commit()
    
    # Create the eke.committees-provided Committees Folder
    createCommitteesFolder(portal)
    transaction.commit()
    
    # Create the new specimens folder
    createSpecimensPage(portal)
    resetIngestPaths(portal)
    transaction.commit()
    
    # Update ingest paths, then ingest the committees folder—and everything else too
    ingestPaths = portal.getProperty('edrnIngestPaths')
    ingestPaths += ('committees',)
    portal.manage_changeProperties(edrnIngestPaths=ingestPaths)
    portal.unrestrictedTraverse('@@ingestEverythingFully')()
    transaction.commit()
    
    # Add a container for Collaborative Groups (the QuickLinks portlet already has a link to it)
    # The new committees must already be ingested because the collaborative groups are built
    # from them (from committees whose type == 'Collaborative Group', specifically)
    createCollaborationsFolder(portal)
    transaction.commit()
    
    # Set up the many_users/many_groups properties
    props = getToolByName(portal, 'portal_properties')
    props.site_properties.manage_changeProperties(many_users=True, many_groups=True)
    transaction.commit()

    # Enable table sorting for everyone
    javascripts = getToolByName(portal, 'portal_javascripts')
    javascripts.getResource('table_sorter.js').setAuthenticated(False)
    javascripts.moveResourceBefore('table_sorter.js', 'dropdown.js')
    addTableSortingNote(portal)
    transaction.commit()

    # Restore annoying link integrity checking
    propTool.site_properties.manage_changeProperties(enable_link_integrity_checks=origLinkIntegrityMode)
    transaction.commit()
    
