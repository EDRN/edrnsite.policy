# encoding: utf-8
# Copyright 2010-2011 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

from plone.i18n.normalizer.interfaces import IIDNormalizer
from Products.CMFCore.utils import getToolByName
from setuphandlers import enableEmbeddableVideos, createCommitteesFolder
from setuphandlers import orderFolderTabs, createSpecimenSearchPage, ingestSpecimens, createMembersListSearchPage
from zope.component import getUtility
from plone.app.viewletmanager.interfaces import IViewletSettingsStorage
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
            'specimens/bank',
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
    qi.installProducts(['p4a.subtyper', 'eea.facetednavigation', 'eke.specimens'])
    setAutoIngestProperties(portal)
    createSpecimenSearchPage(portal)
    ingestSpecimens(portal, setupTool)
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
    
def upgrade1to4(setupTool):
    portal = _getPortal(setupTool)
    catalog = getToolByName(portal, 'portal_catalog')
    catalog.clearFindAndRebuild()
    qi = getToolByName(portal, 'portal_quickinstaller')
    qi.reinstallProducts(_dependencies4)
    for product in _dependencies4:
        qi.upgradeProduct(product)
        transaction.commit()
    qi.installProducts(['p4a.subtyper', 'eea.facetednavigation', 'eke.specimens'])
    installNewPackages(portal, _newPackages4)
    nukeCustomizedLoginForm(portal)
    # Viewlets issue with duplicate colophon?
    # customized login_form issue
    # remove all customized items and migrate into svn code
    # remove DMCC ldap? (to be re-instated by hand later)
    # … or remove both?
    removeExtraViewlets(portal)
    
