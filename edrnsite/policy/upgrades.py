# encoding: utf-8
# Copyright 2010–2012 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

from plone.contentrules.engine.interfaces import IRuleStorage
from plone.app.viewletmanager.interfaces import IViewletSettingsStorage
from plone.i18n.normalizer.interfaces import IIDNormalizer
from Products.CMFCore.utils import getToolByName
from setuphandlers import (
    enableEmbeddableVideos, createCommitteesFolder, createCollaborationsFolder, _doPublish,
    orderFolderTabs, createMembersListSearchPage, createSpecimensPage, disableSpecimenPortlets,
    addTableSortingNote, setEditorProperties, makeFilesVersionable,
    enableJQuery
)
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.publisher.browser import TestRequest
import transaction, re, logging

_logger = logging.getLogger(__name__)

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
# New packages in profile 5:
_newPackages5 = (
    'eea.facetednavigation', # Not really new, but uninstalled prior to 5 so new setup code can take affect
    'eke.specimens', # Not really new, but upgraded the heck out of it
    'edrnsite.vanity', # Will shift to profile 6 since NCI is just now (2013-2-4) installing EDRN Portal 4.2
)
_dependencies5 = (
    'eea.jquery',
    'eke.specimens', # Not really new, but upgraded the heck out of it
    'eke.ecas', # Added indexes
    'edrnsite.collaborations', # New content types
    'eke.committees', # Updated allowed types in content types
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
            'specimens/erne',
        )
        portal.manage_addProperty('edrnIngestPaths', ingestPaths, 'lines')
    if not portal.hasProperty('nonPublishedIngestPaths'):
        nonPublishedIngestPaths = ('biomarkers', 'science-data')
        portal.manage_addProperty('nonPublishedIngestPaths', nonPublishedIngestPaths, 'lines')
    if not portal.hasProperty('nonClearedIngestPaths'):
        nonClearedIngestPaths = ('protocols', 'sites', 'specimens/erne')
        portal.manage_addProperty('nonClearedIngestPaths', nonClearedIngestPaths, 'lines')



def installNewPackages(portal, packageList):
    quickInstaller = getToolByName(portal, 'portal_quickinstaller')
    for package in packageList:
        _logger.info('Installing "%s"', package)
        if quickInstaller.isProductInstalled(package):
            _logger.debug('Package "%s" was already installed', package)
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

def clearLoginLockoutTable(portal):
    '''Clears the login-lockout table. Fixes CA-873.'''
    loginLockoutTool = getToolByName(portal, 'loginlockout_tool')
    lockedAccounts = [i['login'] for i in loginLockoutTool.listAttempts()]
    loginLockoutTool.manage_resetUsers(lockedAccounts)

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
    
    # Make sure we're using the Plone 4 editor, TinyMCE, and not the Plone 3 editor, Kupu
    setEditorProperties(portal)
    transaction.commit()
    
    # Recreate faceted pages
    createMembersListSearchPage(portal)
    transaction.commit()
    
    # Create the eke.committees-provided Committees Folder
    createCommitteesFolder(portal)
    transaction.commit()
    
    # Create the new specimens folder
    createSpecimensPage(portal)
    disableSpecimenPortlets(portal)
    resetIngestPaths(portal)
    transaction.commit()
    
    # Update ingest paths, then ingest the committees & specimens folder—and everything else too
    ingestPaths = portal.getProperty('edrnIngestPaths')
    ingestPaths += ('committees', 'specimens')
    portal.manage_changeProperties(edrnIngestPaths=ingestPaths)
    portal.unrestrictedTraverse('@@ingestEverythingFully')()
    transaction.commit()
    
    # Add a container for Collaborative Groups (the QuickLinks portlet already has a link to it)
    # The new committees must already be ingested because the collaborative groups are built
    # from them (from committees whose type == 'Collaborative Group', specifically).
    # Also, we expect Collaborative Groups to upload & download files, so make them versionable.
    createCollaborationsFolder(portal)
    makeFilesVersionable(portal)
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
    

def upgrade4to5(setupTool):
    _logger.info('Upgrading EDRN Public Portal from profile version 4 to profile version 5')
    portal = _getPortal(setupTool)
    request = portal.REQUEST
    # Whew. Thanks to @davisagli (freakin' brilliant dude) for figuring this out:
    _logger.info("Disabling schema extender's cache")
    from archetypes.schemaextender.extender import disableCache
    disableCache(request)
    # Without the above two lines, we eventually construct an Active ERNE Set during the full ingest below
    # and it mistakenly picks up a Person's schema instead of its own.  When getting its title, a person's
    # is computed, so it looks for a _computeTitle function, but an ActiveERNESet has no such function.
    # Ingest then fails.
    # 
    # Whew!
    # 
    # Now, onward:
    # Disable annoying link integrity checking
    qi = getToolByName(portal, 'portal_quickinstaller')
    propTool = getToolByName(portal, 'portal_properties')
    propTool.site_properties.getProperty('enable_link_integrity_checks', True)
    contentRuleStorage = getUtility(IRuleStorage)
    _logger.info('Disabling link integrity checks')
    propTool.site_properties.manage_changeProperties(enable_link_integrity_checks=False)
    _logger.info('Disabling content rules')
    contentRuleStorage.active = False
    # Clear the catalog
    catalog = getToolByName(portal, 'portal_catalog')
    _logger.info('Clearing the catalog')
    catalog.manage_catalogClear()
    _logger.info('Terminating existing committees with extreme prejudice')
    if 'committees' in portal.keys():
        committees = portal['committees']
        committees.manage_delObjects(committees.keys())
    _logger.info('Enabling JQuery')
    enableJQuery(portal) # Enable jquery.js. Fixes CA-872.
    _logger.info('Disabling Google Analytics')
    removeGoogleAnalytics(portal)
    _logger.info('Clearing the login-lockout table')
    clearLoginLockoutTable(portal) # CA-873
    _logger.info('Installing new packages')
    installNewPackages(portal, _newPackages5)
    _logger.info('Reinstalling products %r', _dependencies5)
    qi.reinstallProducts(_dependencies5)
    for product in _dependencies5:
        _logger.info('Upgrading product "%s"', product)
        qi.upgradeProduct(product)
        transaction.commit()
    if 'specimens' in portal.keys():
        _logger.info('Nuking the specimens tab')
        portal.manage_delObjects('specimens')
    from eke.specimens.upgrades import addSampleSpecimenSets
    # Recreate the members list page to fix the problem with upgrading eea.facetednavigation 4.0rc1→4.5
    _logger.info('Re-creating the members list search page')
    createMembersListSearchPage(portal)
    # Likewise, but for the publications folder: disable and then re-enable faceted view
    if 'publications' in portal.keys():
        publications = portal['publications']
        subtyper = getMultiAdapter((publications, request), name=u'faceted_subtyper')
        _logger.info('Disabling, then re-enabling the faceted subtyper on the publications tab')
        subtyper.disable()
        subtyper.enable()
    _logger.info('Adding sample specimen sets')
    addSampleSpecimenSets(setupTool)
    _logger.info('Disabling portlets on the specimens tab')
    disableSpecimenPortlets(portal)
    _logger.info('Re-setting the auto-ingest paths')
    portal.manage_delProperties(['edrnIngestPaths'])
    setAutoIngestProperties(portal)
    _logger.info('Ingesting everything fully')
    portal.unrestrictedTraverse('@@ingestEverythingFully')()
    _logger.info('Clearing ingest paths to prevent automatic ingest')
    if portal.hasProperty('edrnIngestPaths'):
        portal.manage_delProperties(['edrnIngestPaths'])
    _logger.info('Resetting portal "from" email address')
    portal.manage_changeProperties(email_from_address='sean.kelly@jpl.nasa.gov')
    _logger.info('Clearing, finding, and re-building the catalog')
    catalog.clearFindAndRebuild()
    uidCatalog = getToolByName(portal, 'uid_catalog')
    _logger.info('Rebuilding the UID catalog')
    uidCatalog.manage_rebuildCatalog()
    transaction.commit()
    # We leave link integrity and content rules OFF since at this point the site will be
    # scanned by IBM Rational AppScan and that's sure to screw everything up.

    
