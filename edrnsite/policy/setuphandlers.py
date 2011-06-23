# encoding: utf-8
# Copyright 2009 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

from eea.facetednavigation.interfaces import ICriteria
from eke.biomarker.interfaces import IBiomarker
from eke.biomarker.utils import COLLABORATIVE_GROUP_BMDB_IDS_TO_NAMES
from eke.committees.interfaces import ICommittee
from eke.ecas.interfaces import IDataset
from eke.ecas.utils import COLLABORATIVE_GROUP_ECAS_IDS_TO_NAMES
from eke.site.interfaces import IPerson
from eke.specimens import SPECIMEN_TYPE_VOCAB_NAME, STORAGE_VOCAB_NAME
from eke.specimens.interfaces import ISpecimenRecord
from p4a.subtyper.interfaces import ISubtyper
from plone.app.contentrules.rule import get_assignments
from plone.app.ldap.engine.interfaces import ILDAPConfiguration
from plone.app.ldap.engine.schema import LDAPProperty
from plone.app.ldap.engine.server import LDAPServer
from plone.app.ldap.ploneldap.util import guaranteePluginExists
from plone.app.linkintegrity.interfaces import ILinkIntegrityInfo
from plone.contentrules.engine.assignments import RuleAssignment
from plone.contentrules.engine.interfaces import IRuleStorage, IRuleAssignmentManager
from plone.portlets.interfaces import IPortletManager, IPortletAssignmentMapping
from Products.CMFCore.permissions import MailForgottenPassword
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.WorkflowCore import WorkflowException
from ZODB.DemoStorage import DemoStorage
from zope.component import getMultiAdapter, getUtility, queryUtility
from zope.publisher.browser import TestRequest
import urllib2, os, sys, logging

_logger = logging.getLogger('Plone')

_edrnHomePageDescription = u'''The Early Detection Research Network (EDRN), an initiative of the National Cancer Institute (NCI), brings together dozens of institutions to help accelerate the translation of biomarker information into clinical applications and to evaluate new ways of testing cancer in its earliest stages and for cancer risk.
'''
_edrnHomePageBodyHTML = u'''<table><tbody>
<tr><td><a href="about-edrn/scicomponents">&#x25ba;&#x00a0;Scientific Components</a></td>
<td><a href="advocates">&#x25ba;&#x00a0;For Public, Patients, Advocates</a></td></tr>
<tr><td><a href="colops">&#x25ba;&#x00a0;Collaborative Opportunities</a> (how to join EDRN)</td>
<td><a href="researchers">&#x25ba;&#x00a0;For Researchers</a></td></tr>
</tbody></table>'''

_staticResourcesBaseURL = 'http://cancer.jpl.nasa.gov/static/'
_edrnContentEvents = ('edrn-add-event', 'edrn-mod-event', 'edrn-del-event', 'edrn-pub-event')
_edrnContentEventFolders = (
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

def disablePresentationMode(portal):
    '''Turn off front page's presentation mode.'''
    if portal['front-page'].presentation:
        portal['front-page'].presentation = False

def privatizePloneFolders(portal):
    '''Make Plone's default folders of Members, News, and Events private.'''
    wfTool = getToolByName(portal, 'portal_workflow')
    for i in ('Members', 'news', 'events'):
        if i not in portal.objectIds():
            continue
        if wfTool.getInfoFor(portal[i], 'review_state') != 'private':
            wfTool.doActionFor(portal[i], action='retract')

def addGoogleVerificationPage(portal):
    '''Add a verification page for Google Webmaster tools.'''
    if 'google6303b8e42ec16379.html' not in portal.objectIds():
        portal.manage_addProduct['PageTemplates'].manage_addPageTemplate(
            id='google6303b8e42ec16379.html', title='Google Verification',
            text=u"<tal:content replace='string:google-site-verification: google6303b8e42ec16379.html'/>"
        )

def connectLDAP(portal):
    '''Set up LDAP parameters.'''
    ldapConfig = getUtility(ILDAPConfiguration)
    if ldapConfig.user_object_classes == 'edrnPerson':
        # Already configured
        return
    ldapConfig.user_object_classes = 'edrnPerson'
    ldapConfig.ldap_type = u'LDAP'
    ldapConfig.user_scope = 1
    ldapConfig.user_base = 'dc=edrn,dc=jpl,dc=nasa,dc=gov'
    for i in ldapConfig.servers.keys():
        del ldapConfig.servers[i]
    ldapConfig.servers['ldapserver-1'] = LDAPServer(
        'cancer.jpl.nasa.gov', connection_type=1, connection_timeout=5, operation_timeout=15, enabled=True
    )
    p = ldapConfig.schema['uid']
    p.ldap_name, p.plone_name, p.description, p.multi_valued = 'uid', '', u'User ID', False
    p = ldapConfig.schema['mail']
    p.ldap_name, p.plone_name, p.description, p.multi_valued = 'mail', 'email', u'Email Address', False
    p = ldapConfig.schema['cn']
    p.ldap_name, p.plone_name, p.description, p.multi_valued = 'cn', 'fullname', u'Full Name', False
    p = ldapConfig.schema['sn']
    p.ldap_name, p.plone_name, p.description, p.multi_valued = 'sn', '', u'Surname', False
    ldapConfig.schema['description'] = LDAPProperty('description', 'description', u'Description', False)
    ldapConfig.userid_attribute = 'uid'
    ldapConfig.rdn_attribute = 'uid'
    ldapConfig.login_attribute = 'uid'
    ldapConfig.group_scope = 1
    ldapConfig.group_base = 'dc=edrn,dc=jpl,dc=nasa,dc=gov'
    ldapConfig.bind_password = '70ve4edrn!'
    ldapConfig.bind_dn = 'uid=admin,ou=system'
    guaranteePluginExists()
    # To enable accurate counts of failed attempts by LoginLockout:
    portal.acl_users['ldap-plugin'].acl_users.setCacheTimeout('negative', 0)

def _doPublish(item, wfTool):
    try:
        wfTool.doActionFor(item, action='publish')
        item.reindexObject()
    except WorkflowException:
        pass
    for i in item.objectIds():
        subItem = item[i]
        _doPublish(subItem, wfTool)

def ingestSpecimens(portal, context):
    # New in profile version 1 (software version 1.0.2)
    targetFolder = portal['specimens']
    if 'bank' in targetFolder.objectIds():
        request = getattr(targetFolder, 'REQUEST')
        getattr(request, 'environ')[ILinkIntegrityInfo(request).getEnvMarker()] = 'all'
        targetFolder.manage_delObjects('bank')
    specimensFolder = targetFolder[targetFolder.invokeFactory('Specimen Folder', 'bank')]
    specimensFolder.title = 'Bank'
    specimensFolder.description = 'Medical samples and other specimens from both cancer-positive and cancer-negative participants, as well as reference sets of specimens.'
    _doPublish(specimensFolder, getToolByName(portal, 'portal_workflow'))
    specimensFolder.reindexObject()
    ingestor = getMultiAdapter((specimensFolder, TestRequest()), name=u'ingest')
    ingestor.render = False
    try:
        ingestor()
    except:
        pass

def _ingest(rootPath, path, traverse, url, force=False):
    '''Ingest into a folder at path rooted at rootPath using given traverse function. Set the RDF data source
    for the folder to the given url. Return True if we ingested something, False if not.'''
    path = rootPath + path
    item = traverse(path)
    if len(item.objectIds()) > 0 and not force:
        # Already populated, no need to re-ingest at this time, unless overridden by force = True
        return False
    item.rdfDataSource = url
    item.manage_delObjects(item.objectIds())
    ingestor = getMultiAdapter((item, TestRequest()), name=u'ingest')
    ingestor.render = False
    try:
        ingestor()
        return True
    except urllib2.HTTPError, ex:
        print >>sys.stderr, 'Failure ingesting from %s: %s; pressing on!' % (url, str(ex))
        return False

def ingestInitially(portal, context):
    # FIXME: need to touch import profile context's _profile_path to construct URLs to our RDF data
    didIngests = False
    urlPrefix = u'file:%s/rdf/' % context._profile_path
    traverse = portal.restrictedTraverse
    rootPath = portal.getPhysicalPath()
    for path, url in (
        (('resources', 'body-systems'), urlPrefix + 'body-systems.rdf'),
        (('resources', 'diseases'), urlPrefix + 'diseases.rdf'),
        (('resources', 'miscellaneous-resources'), urlPrefix + 'resources.rdf'),
        (('protocols',), urlPrefix + 'protocols.rdf'),
    ):
        rc = _ingest(rootPath, path, traverse, url, didIngests)
        if rc: didIngests = True
    # These folders must be separate because they have multiple RDF URLs
    biomarkers, sites, publications = portal['biomarkers'], portal['sites'], portal['publications']
    if len(biomarkers.objectIds()) == 0 or len(sites.objectIds()) == 0 or len(publications.objectIds()) == 0 or didIngests:
        # No data yet, do initial ingest
        biomarkers.rdfDataSource = urlPrefix + 'biomarkers.rdf'
        biomarkers.bmoDataSource = urlPrefix + 'biomarkerorgans.rdf'
        publications.rdfDataSource = urlPrefix + 'dmcc-pubs.rdf'
        publications.additionalDataSources = [urlPrefix + 'bmdb-pubs.rdf']
        sites.rdfDataSource = urlPrefix + 'sites.rdf'
        sites.peopleDataSource = urlPrefix + 'people.rdf'
        for folder in (sites, publications, biomarkers):
            ingestor = getMultiAdapter((folder, TestRequest()), name=u'ingest')
            _logger.warn('INGESTING on %r from %s', folder, folder.rdfDataSource)
            ingestor.render = False
            ingestor()
            didIngests = True
    # Re-ingest protocols now that sites are in. Oh, and that means we can do
    # science data now, too.  And the new committees.
    for path, url in (
        (('science-data',), urlPrefix + 'datasets.rdf'),
        (('protocols',), urlPrefix + 'protocols.rdf'),
        (('science-data',), urlPrefix + 'datasets.rdf'),
        (('committees',), urlPrefix + 'committees.rdf')
    ):
        rc = _ingest(rootPath, path, traverse, url, didIngests)
        if rc: didIngests = True
    # Once more, re-connect biomarkers to science data now that it's available
    if didIngests:
        biomarkers.manage_delObjects(biomarkers.objectIds())
        ingestor = getMultiAdapter((biomarkers, TestRequest()), name=u'ingest')
        ingestor.render = False
        ingestor()


def publishKnowledge(portal):
    wfTool = getToolByName(portal, 'portal_workflow')
    items = portal.objectIds()
    for i in (
        'publications', 'resources', 'sites', 'protocols', 'about-edrn', 'advocates', 'colops', 'docs',
        'funding-opportunities', 'researchers', 'admin', 'committees',
    ):
        if i not in items:
            continue
        item = portal[i]
        if wfTool.getInfoFor(item, 'review_state') != 'published':
            _doPublish(item, wfTool)
    # Biomarkers get their publication state during ingest, so all we have to do is
    # publish the biomarker folder:
    if 'biomarkers' in items:
        bmFolder = portal['biomarkers']
        if wfTool.getInfoFor(bmFolder, 'review_state') != 'published':
            wfTool.doActionFor(bmFolder, 'publish')
    # Same with science data
    if 'science-data' in items:
        ecasFolder = portal['science-data']
        if wfTool.getInfoFor(ecasFolder, 'review_state') != 'published':
            wfTool.doActionFor(ecasFolder, 'publish')
    # These folders shouldn't appear as tabs, though:
    for i in (
        'advocates', 'colops', 'docs', 'funding-opportunities', 'researchers', 'sites', 'admin', 'committees'
    ):
        item = portal[i]
        if not item.getExcludeFromNav():
            item.setExcludeFromNav(True)
            item.reindexObject()

def importOtherContent(portal, context):
    testing = isinstance(portal._p_jar.db()._storage, DemoStorage)
    ids = portal.objectIds()
    for objID, title in (
        ('about-edrn', 'About EDRN'),
        ('committees', 'Committees'),
        ('resources', 'Resources'),
        ('advocates', 'Public, Patients, and Advocaetes'),
        ('colops', 'Collaborative Opportunities'),
        ('researchers', 'For Researchers'),
        ('docs', 'Bookshelf'),
        ('funding-opportunities', 'Funding Opportunities'),
    ):
        if objID in ids:
            continue
        if testing:
            # Don't bother importing the huge content into the test database.
            # It just won't fit. Instead, just make the folder.
            folder = portal[portal.invokeFactory('Folder', objID)]
            folder.setTitle(title)
            folder.reindexObject()
        else:
            fn = objID + '.zexp'
            f = context.openDataFile(fn)
            # Do we have the .zexp file?
            if f is None:
                # No, download it.
                s = d = None
                try:
                    # FIXME: Need to touch private _profile_path because we want to write to our
                    # export context, and the 'openDataFile' method of an export context opens for
                    # reading only.
                    s, d = urllib2.urlopen(_staticResourcesBaseURL + fn), open(os.path.join(context._profile_path, fn), 'w')
                    while True:
                        buf = s.read(4096)
                        if len(buf) == 0:
                            break
                        d.write(buf)
                finally:
                    for i in s, d:
                        try:
                            if i is not None:
                                i.close()
                        except IOError:
                            pass
                f = context.openDataFile(fn)
                # Now do we have it?
                if f is None:
                    # No, give up.
                    continue
            # We do have it. Close it; we just need its name.
            f.close()
            # FIXME: Need to touch private _importObjectFromFile because the other
            # import method expects items from the instance's import directory and
            # not the profiles/default directory.
            portal._importObjectFromFile(str(f.name))

def createMiscKnowledgeFolders(portal):
    resources = portal['resources']
    if resources.Title() != u'Resources':
        resources.setTitle(u'Resources')
        resources.reindexObject()
    for objID, title, description, portalType in (
        ('body-systems', u'Body Systems', u'Body systems are parts of the body, such as organs.', 'Knowledge Folder'),
        ('diseases', u'Diseases', u'Diseases afflict body systems, such as cancer.', 'Knowledge Folder'),
        ('miscellaneous-resources', u'Miscellaneous Resources', u'Various other resources.', 'Knowledge Folder'),
    ):
        if objID in resources.objectIds(): continue
        obj = resources[resources.invokeFactory(portalType, objID)]
        obj.title = title
        obj.description = description
        obj.reindexObject()
    if 'science-data' not in portal.objectIds():
        obj = portal[portal.invokeFactory('Dataset Folder', 'science-data')]
        obj.title = u'Science Data'
        obj.description = u'Data collected about science.'
        obj.reindexObject()

def deleteDefaultPortlets(portal):
    column = getUtility(IPortletManager, name=u'plone.leftcolumn')
    manager = getMultiAdapter((portal, column), IPortletAssignmentMapping)
    # Left column: nuke all but the review list and quick links
    for i in manager.keys():
        if i not in ('review-list', 'search', 'edrn-quick-links'):
            del manager[i]
    column = getUtility(IPortletManager, name=u'plone.rightcolumn')
    manager = getMultiAdapter((portal, column), IPortletAssignmentMapping)
    # Right column: nuke all but the DMCC RSS feeds
    for i in manager.keys():
        if not i.startswith('DMCCRSS-') and i != 'search':
            del manager[i]

def orderFolderTabs(portal):
    # about < bio < proto < science data < specimens < pubs < resources
    idx = portal.getObjectPosition('about-edrn')
    idx += 1
    for i in ('biomarkers', 'protocols', 'science-data', 'specimens', 'publications', 'resources'):
        portal.moveObject(i, idx)
        idx += 1
    ploneUtils = getToolByName(portal, 'plone_utils')
    ploneUtils.reindexOnReorder(portal)

def setupLoginLockout(portal):
    '''Configure the login-lockout mechanism to lockout accounts with too many failures'''
    lockoutPlugin = portal.acl_users.login_lockout_plugin
    if lockoutPlugin.getProperty('_max_attempts', 0) != 6 or lockoutPlugin.getProperty('_reset_period', 0.0) != 0.25:
        # Not yet configured; configure it:
        lockoutPlugin.manage_changeProperties(_max_attempts=6, _reset_period=0.25) # 5 tries in 15 minutes; lock on 6th
        lockoutPage = lockoutPlugin['lockout']
        lockoutPage.pt_edit(u'''<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en"
      xmlns:tal="http://xml.zope.org/namespaces/tal"
      xmlns:metal="http://xml.zope.org/namespaces/metal"
      xmlns:i18n="http://xml.zope.org/namespaces/i18n"
      lang="en"
      metal:use-macro="here/main_template/macros/master"
      i18n:domain="edrnsite.policy">
<head>
    <metal:block fill-slot="top_slot"
                 tal:define="dummy python:request.set('disable_border',1)" />
    <metal:block fill-slot="column_one_slot" />
    <metal:block fill-slot="column_two_slot" />
    <title i18n:translate='loginLockedTitle'>Login</title>
</head>

<body>
<div metal:fill-slot="main">
<dl tal:condition='isAnon|nothing' class='portalMessage error'>
<dt i18n:translate='error'>Error</dt>
<dd i18n:translate='loginLocked'>
Login failed. Please contact the <a i18n:name='contact' href="mailto:heather.kincaid@jpl.nasa.gov">Informatics Center</a> for assistance.
</dd>
</dl>
</div>
</body>
</html>''', 'text/html')

def createWelcomePage(portal):
    if 'front-page' in portal.objectIds():
        if portal['front-page'].portal_type == 'EDRN Home': return
        portal.manage_delObjects('front-page')
    frontPage = portal[portal.invokeFactory('EDRN Home', 'front-page')]
    frontPage.setTitle('Welcome to EDRN')
    frontPage.setDescription(_edrnHomePageDescription)
    frontPage.setText(_edrnHomePageBodyHTML)
    frontPage.showGarishSearchBox = True
    wfTool = getToolByName(portal, 'portal_workflow')
    wfTool.doActionFor(frontPage, action='publish')
    frontPage.reindexObject()

def addAdminstriviaImages(portal, context):
    '''The GenericSetup profile imports pages and folders just fine, but can't handle images.
    So, add the missing images.'''
    imageFolder = portal['admin']['images']
    for objID, title, description in (
        ('excel.gif', u'Excel',                    u'Icon for .xls files.'),
        ('flash.gif', u'Flash',                    u'Icon for .swf files.'),
        ('pdf.gif',   u'Portable Document Format', u'Icon for .pdf files.'),
        ('ppt.gif',   u'PowerPoint',               u'Icon for .ppt files.'),
        ('qt.gif',    u'Quicktime',                u'Icon for Apple Quicktime files.'),
        ('word.gif',  u'Word',                     u'Icon for .doc files'),
    ):
        if objID in imageFolder.objectIds():
            continue
        image = imageFolder[imageFolder.invokeFactory('Image', objID)]
        image.setTitle(title)
        image.setDescription(description)
        image.setImage(context.readDataFile(objID), mimetype='image/gif', content_type='image/gif', filename=objID)
        image.reindexObject()
    if imageFolder.getLayout() != 'atct_album_view':
        imageFolder.setLayout('atct_album_view')

def setIngestURLs(portal):
    '''Set up the URLs knowledge folders will use for future ingests.'''
    portal.resources['body-systems'].rdfDataSource            = 'http://ginger.fhcrc.org/dmcc/rdf-data/body-systems/rdf'
    portal.resources['diseases'].rdfDataSource                = 'http://ginger.fhcrc.org/dmcc/rdf-data/diseases/rdf'
    portal.resources['miscellaneous-resources'].rdfDataSource = 'http://edrn.jpl.nasa.gov/bmdb/rdf/resources'
    portal['biomarkers'].bmoDataSource                        = 'http://edrn.jpl.nasa.gov/bmdb/rdf/biomarkerorgans'
    portal['biomarkers'].rdfDataSource                        = 'http://edrn.jpl.nasa.gov/bmdb/rdf/biomarkers'
    portal['protocols'].rdfDataSource                         = 'http://ginger.fhcrc.org/dmcc/rdf-data/protocols/rdf'
    portal['publications'].additionalDataSources              = ['http://edrn.jpl.nasa.gov/bmdb/rdf/publications']
    portal['publications'].rdfDataSource                      = 'http://ginger.fhcrc.org/dmcc/rdf-data/publications/rdf'
    portal['sites'].peopleDataSource                          = 'http://ginger.fhcrc.org/dmcc/rdf-data/registered-person/rdf'
    portal['sites'].rdfDataSource                             = 'http://ginger.fhcrc.org/dmcc/rdf-data/sites/rdf'
    portal['committees'].rdfDataSource                        = 'http://ginger.fhcrc.org/dmcc/rdf-data/committees/rdf'
    # Beware: long URL
    portal['science-data'].rdfDataSource = 'http://edrn.jpl.nasa.gov/fmprodp3/rdf/dataset?' + \
        'type=ALL&baseUrl=http://edrn.jpl.nasa.gov/ecas/dataset.php'

def empowerSuperUserGroup(context):
    '''Give people in the Super User group great power.  This assumes that
    LDAP is up and has a cn=Super User,dc=edrn,dc=jpl,dc=nasa,dc=gov.'''
    groupsTool = getToolByName(context, 'portal_groups')
    superUser = groupsTool.getGroupById('Super User')
    if superUser is None or 'Manager' not in superUser.getRoles():
        try:
            groupsTool.editGroup('Super User', roles=['Manager'])
        except (KeyError, NotImplementedError):
            pass


def disableDiscussion(context):
    '''Per http://oodt.jpl.nasa.gov/jira/browse/CA-435, no discussion allowed anywhere'''
    typesTool = getToolByName(context, 'portal_types')
    for t in typesTool.objectIds():
        if typesTool[t].allow_discussion:
            typesTool[t].allow_discussion = False

def disablePasswordEmails(portal):
    '''Per CA-498, get rid of password-reset emails'''
    roles = portal.rolesOfPermission(MailForgottenPassword)         # Get the current roles for the mail-forgotten-pw perm
    for role in roles:                                              # Check each role
        if role['selected']:                                        # Found one that's enabled?
            portal.manage_permission(MailForgottenPassword, [], 0)  # Yep. Clear 'em all!
            return                                                  # Don't need to check the others now

def assignContentRulesToContainer(container, storage, bubbles):
    '''Assign the standard EDRN content events to the given container.'''
    assignmentManager = IRuleAssignmentManager(container, None)
    if assignmentManager is None:
        # This container doesn't support content rules, so skip it.
        return
    for eventName in _edrnContentEvents:
        assignment = assignmentManager.get(eventName, None)
        if assignment is None:
            # Brand new assignment
            assignment = assignmentManager[eventName] = RuleAssignment(eventName)
        if not assignment.enabled:
            assignment.enabled = True
        if assignment.bubbles != bubbles:
            assignment.bubbles = bubbles
        path = '/'.join(container.getPhysicalPath())
        get_assignments(storage[eventName]).insert(path)

def assignContentRules(portal):
    '''Install content rules on select folders.  We do this here because the
    assignments from contentrules.xml most likely have failed since much of
    the content was created here.'''
    storage = queryUtility(IRuleStorage)
    if storage is None:
        # No content rule storage? Nothing to do.
        return
    # The root of the site gets the standard EDRN rules, but they don't bubble down:
    assignContentRulesToContainer(portal, storage, bubbles=False)
    # These folders also get the standard EDRN rules, but they DO bubble down:
    for folderName in _edrnContentEventFolders:
        folder = portal.unrestrictedTraverse(folderName)
        assignContentRulesToContainer(folder, storage, bubbles=True)

def createMembersListSearchPage(portal):
    '''Create the members list page'''
    # New in profile version 1 (software version 1.0.2):
    if 'members-list' in portal.objectIds():
        portal.manage_delObjects('members-list')
    membersList = portal[portal.invokeFactory('Folder', 'members-list')]
    membersList.setTitle('Members List')
    membersList.setDescription('EDRN member sites, investigators, and staff.')
    membersList.setExcludeFromNav(True)
    _doPublish(membersList, getToolByName(portal, 'portal_workflow'))
    subtyper = getUtility(ISubtyper)
    subtyper.change_type(membersList, 'eea.facetednavigation.FolderFacetedNavigable')
    criteria = ICriteria(membersList)
    for cid in criteria.keys():
        criteria.delete(cid)
    criteria.add('resultsperpage', 'bottom', 'default', title='Results per page', hidden=True, start=0, end=50, step=5, default=20)
    criteria.add('sorting', 'bottom', 'default', title='Sort on', hidden=True, default='sortable_title')
    criteria.add(
        'checkbox', 'bottom', 'default',
        title='Obj provides',
        hidden=True,
        index='object_provides',
        operator='or',
        vocabulary=u'eea.faceted.vocabularies.ObjectProvides',
        default=[IPerson.__identifier__],
        count=False,
        maxitems=0,
        sortreversed=False,
        hidezerocount=False
    )
    criteria.add(
        'checkbox', 'left', 'default',
        title='Investigator',
        hidden=False,
        index='piUID',
        operator='or',
        vocabulary=u'eke.site.PrincipalInvestigators',
        count=False,
        maxitems=4,
        sortreversed=False,
        hidezerocount=False
    )
    criteria.add(
        'checkbox', 'left', 'default',
        title='Type',
        index='investigatorStatus',
        operator='or',
        vocabulary=u'eke.site.NotPeons',
        count=True,
        maxitems=0,
        sortreversed=False,
        hidezerocount=False
    )
    criteria.add(
        'checkbox', 'left', 'default',
        title='Sites',
        hidden=False,
        index='siteName',
        operator='or',
        vocabulary=u'eke.site.SitesNames',
        count=True,
        maxitems=4,
        sortreversed=False,
        hidezerocount=False
    )
    criteria.add(
        'checkbox', 'left', 'default',
        title='Type',
        hidden=False,
        index='memberType',
        operator='or',
        vocabulary=u'eke.site.MemberType',
        count=True,
        maxitems=8,
        sortreversed=False,
        hidezerocount=False
    )
    criteria.add('debug', 'top', 'default', title='Debug Criteria', user='kelly')
    criteria.add('criteria', 'top', 'default', title='Current Search')
    membersList.reindexObject()

def createSpecimenSearchPage(portal):
    '''Create the specimen search page'''
    # New in profile version 1 (software version 1.0.2):
    if 'specimens' in portal.objectIds():
        portal.manage_delObjects('specimens')
    specimens = portal[portal.invokeFactory('Folder', 'specimens')]
    specimens.setTitle('Specimens')
    specimens.setDescription('Search for specimens collected by EDRN members.')
    _doPublish(specimens, getToolByName(portal, 'portal_workflow'))
    subtyper = getUtility(ISubtyper)
    subtyper.change_type(specimens, 'eea.facetednavigation.FolderFacetedNavigable')
    criteria = ICriteria(specimens)
    for cid in criteria.keys():
        criteria.delete(cid)
    criteria.add('resultsperpage', 'bottom', 'default', title='Results per page', hidden=True, start=0, end=50, step=5, default=20)
    criteria.add('sorting', 'bottom', 'default', title='Sort on', hidden=True, default='sortable_title(reverse)')
    criteria.add(
        'checkbox', 'bottom', 'default',
        title='Obj provides',
        hidden=True,
        index='object_provides',
        operator='or',
        vocabulary=u'eea.faceted.vocabularies.ObjectProvides',
        default=[ISpecimenRecord.__identifier__],
        count=False,
        maxitems=0,
        sortreversed=False,
        hidezerocount=False
    )
    criteria.add(
        'checkbox', 'left', 'default',
        title='Site',
        hidden=False,
        index='siteName',
        operator='or',
        vocabulary='eke.specimens.ERNESites',
        count=False,
        maxitems=6,
        sortreversed=False,
        hidezerocount=False
    )
    criteria.add(
        'checkbox', 'left', 'default',
        title='Collection',
        hidden=False,
        index='specimenType',
        operator='or',
        vocabulary=SPECIMEN_TYPE_VOCAB_NAME,
        count=False,
        maxitems=6,
        sortreversed=False,
        hidezerocount=False
    )
    criteria.add(
        'checkbox', 'left', 'default',
        title='Storage',
        index='storageType',
        operator='or',
        vocabulary=STORAGE_VOCAB_NAME,
        count=False,
        maxitems=6,
        sortreversed=False,
        hidezerocount=False
    )
    criteria.add(
        'checkbox', 'left', 'default',
        title='Cancer Diagnosis',
        index='cancerDiagnosis',
        operator='or',
        vocabulary=u'eke.specimens.CancerDiagnosisVocabulary',
        count=False,
        maxitems=0,
        sortreversed=False,
        hidezerocount=False
    )
    criteria.add('debug', 'top', 'default', title='Debug Criteria', user='kelly')
    criteria.add('criteria', 'top', 'default', title='Current Search')
    specimens.reindexObject()


def enableEmbeddableVideos(portal):
    '''Allow use of YouTube tags'''
    # New in profile version 1 (software version 1.0.2):
    safeHTMLxform = getToolByName(portal, 'portal_transforms')['safe_html']
    params = {
        'valid_tags': {
            'pre': '1', 'em': '1', 'code': '1', 'p': '1', 'h2': '1', 'h3': '1', 'h1': '1', 'h6': '1', 'dl': '1', 'h4': '1',
            'h5': '1', 'meta': '0', 'table': '1', 'span': '1', 'sub': '1', 'img': '0', 'title': '1', 'tt': '1', 'tr': '1',
            'tbody': '1', 'li': '1', 'hr': '0', 'dfn': '1', 'tfoot': '1', 'th': '1', 'sup': '1', 'var': '1', 'del': '1',
            'td': '1', 'samp': '1', 'cite': '1', 'ul': '1', 'thead': '1', 'body': '1', 'map': '1', 'head': '1', 'blockquote': '1',
            'ins': '1', 'acronym': '1', 'big': '1', 'dd': '1', 'base': '0', 'kbd': '1', 'br': '0', 'address': '1', 'dt': '1',
            'strong': '1', 'b': '1', 'a': '1', 'ol': '1', 'colgroup': '1', 'i': '1', 'area': '1', 'html': '1', 'q': '1',
            'caption': '1', 'bdo': '1', u'u': '1', 'small': '1', 'div': '1', 'col': '1', 'abbr': '1',
            'object': '1', 'param': '1', 'embed': '1'
        },
        'nasty_tags': {u'applet': 1, u'script': 1}
    }
    for k in list(params):
        if isinstance(params[k], dict):
            v = params[k]
            params[k+'_key'] = v.keys()
            params[k+'_value'] = [str(s) for s in v.values()]
            del params[k]
    safeHTMLxform.set_parameters(**params)
    safeHTMLxform._p_changed = True
    safeHTMLxform.reload()

def createKnowledgeFolders(portal):
    existing = portal.objectIds()
    for objID, kind, title, desc in (
        ('biomarkers', 'Biomarker Folder', u'Biomarkers', u'Cancer biomarkers currently being evaluated by the EDRN.'),
        ('protocols', 'Study Folder', u'Protocols', u'Studies, projects, protocols, and other research fronts.'),
        ('publications', 'Publication Folder', u'Publications', u'Articles, papers, journal entries, books, and other publications.'),
        ('sites', 'Site Folder', u'Sites', u'Member institutions and other sites of the Early Detection Research Network.'),
    ):
        if objID in existing: continue
        obj = portal[portal.invokeFactory(kind, objID)]
        obj.setTitle(title)
        obj.setDescription(desc)
        obj.reindexObject()

def createCollaborationsFolder(portal):
    # New in profile version 4 (software version 1.1.2)
    wfTool = getToolByName(portal, 'portal_workflow')
    if 'collaborative-groups' in portal.keys():
        f = portal['collaborative-groups']
        if f.portal_type == 'Collaborations Folder': return
        portal.manage_delObjects('collaborative-groups')
    f = portal[portal.invokeFactory('Collaborations Folder', 'collaborative-groups')]
    f.setTitle(u'Collaborative Groups')
    f.setDescription(u'Collaborative groups are people that work together.')
    f.setExcludeFromNav(True)
    _doPublish(f, wfTool)
    f.reindexObject()
    # Populate it: find all Committee objects that are of type "Collaborative Group" and use that to
    # create the Collaborative Group objects
    catalog = getToolByName(portal, 'portal_catalog')
    datasets = [i.getObject() for i in catalog(object_provides=IDataset.__identifier__)]
    if len(datasets) == 0:
        _logger.warn('No datasets found via catalog. Cannot link collaborative groups to them.')
    biomarkers = [i.getObject() for i in catalog(object_provides=IBiomarker.__identifier__)]
    if len(biomarkers) == 0:
        _logger.warn('No biomarkers found via catalog. Cannot link collaborative groups to them.')
    results = [i.getObject() for i in catalog(object_provides=ICommittee.__identifier__, committeeType='Collaborative Group')]
    _logger.info('Found %d Committee objects of type "Collaborative Group" via the catalog', len(results))
    if len(results) == 0 and 'committees' in portal.keys() and 'collaborative-groups' in portal['committees'].keys():
        # Not found via catalog? Ugh, this must be an upgrade and our catalog is out of date.
        # In that case, do it the manual way.
        cbfolder = portal['committees']['collaborative-groups']
        for i in cbfolder.keys():
            cb = cbfolder[i]
            results.append(cb)
        _logger.info('OK, found %d Committee collaborative groups directly in the expected folder instead', len(results))
    for committee in results:
        cbg = f[f.invokeFactory('Collaborative Group', committee.id)]
        cbg.setTitle(committee.title)
        cbg.setDescription(committee.description)
        index = cbg[cbg.invokeFactory('Collaborative Group Index', 'index_html')]
        index.setTitle(committee.title)
        index.setDescription(committee.description)
        members = []
        members.extend(committee.member)
        members.extend(committee.consultant)
        members.extend(committee.coChair)
        members.extend(committee.chair)
        # Add the members of the group
        index.setMembers(members)
        # Add the datasets that belong to this group
        groupDatasets = []
        for dataset in datasets:
            cbName = COLLABORATIVE_GROUP_ECAS_IDS_TO_NAMES.get(dataset.collaborativeGroup, None)
            if cbName == committee.title:
                groupDatasets.append(dataset)
        index.setDatasets(groupDatasets)
        # And the biomarkers being studied by this group
        groupBiomarkers = []
        for biomarker in biomarkers:
            groupNames = [i[0] for i in biomarker.get_local_roles()]
            for groupName in groupNames:
                cbName = COLLABORATIVE_GROUP_BMDB_IDS_TO_NAMES.get(groupName, None)
                if cbName == committee.title:
                    groupBiomarkers.append(biomarker)
                    break
        index.setBiomarkers(groupBiomarkers)
        _doPublish(cbg, wfTool)
        cbg.reindexObject()
    # C'est tout.

def createCommitteesFolder(portal):
    # New in profile version 1 (software version 1.0.3)
    if 'committees' in portal.objectIds():
        committees = portal['committees']
        if committees.portal_type == 'Committee Folder': return
        request = getattr(portal, 'REQUEST')
        getattr(request, 'environ')[ILinkIntegrityInfo(request).getEnvMarker()] = 'all'
        # WTF: bug in plone.app.linkintegrity-1.0.12 line 43 AttributeError: 'NoneType' object has no attribute 'UID'
        try:
            portal.manage_delObjects('committees')
        except AttributeError:
            # OK, that was #fail. Try it without events.
            try: portal._delObject('committees', suppress_events=True)
            except AttributeError: pass
    committees = portal[portal.invokeFactory('Committee Folder', 'committees')]
    committees.setTitle(u'Committees')
    committees.setDescription(u'The following describes the committees, subcommittees, and other components of EDRN.')
    committees.rdfDataSource = u'http://ginger.fhcrc.org/dmcc/rdf-data/committees/rdf'
    committees.setExcludeFromNav(True)
    committees.reindexObject()
    
def rebuildCatalog(portal):
    # Don't trust the catalog as delivered from NCI
    catalog = getToolByName(portal, 'portal_catalog')
    catalog.clearFindAndRebuild()


def setupVarious(context):
    '''Miscellaneous import steps.'''
    if context.readDataFile('edrnsite.policy.flag.txt') is None:
        return
    portal = context.getSite()
    rebuildCatalog(portal)
    importOtherContent(portal, context)
    addAdminstriviaImages(portal, context)
    createKnowledgeFolders(portal)
    createMiscKnowledgeFolders(portal)
    disablePresentationMode(portal)
    privatizePloneFolders(portal)
    addGoogleVerificationPage(portal)
    connectLDAP(portal)
    createCommitteesFolder(portal)
    ingestInitially(portal, context)
    createSpecimenSearchPage(portal)
    ingestSpecimens(portal, context)
    deleteDefaultPortlets(portal)
    publishKnowledge(portal)
    orderFolderTabs(portal)
    setIngestURLs(portal)
    empowerSuperUserGroup(portal)
    disableDiscussion(portal)
    disablePasswordEmails(portal)
    assignContentRules(portal)
    setupLoginLockout(portal)
    createWelcomePage(portal)
    createMembersListSearchPage(portal)
    enableEmbeddableVideos(portal)
    createCollaborationsFolder(portal)
