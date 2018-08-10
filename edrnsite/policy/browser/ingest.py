# encoding: utf-8
# Copyright 2010–2018 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

'''EDRN Site Policy: browser capabilities: ingestion.'''

from Acquisition import aq_inner
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.Five.browser import BrowserView
from zope.component import getMultiAdapter, getUtility
from plone.contentrules.engine.interfaces import IRuleStorage
from plone.app.linkintegrity.interfaces import ILinkIntegrityInfo
import logging, plone.api, datetime, transaction

_logger = logging.getLogger(__name__)

# These folders set their publication state based on security directives in their
# RDF streams (or in their ingest code), and therefore don't need a manual publication step.
_doNotPublish = ('biomarkers', 'science-data', 'specimens')

# These folders update their contents and require no deletion beforehand
_doNotDelete = ('protocols', 'sites', 'specimens')

# Where to email the ingest report TO DO: use something generic!
_defaultIngestReportEmail = 'edrn-portal@jpl.nasa.gov'


class FullIngestor(BrowserView):
    '''Perform a full ingest from our external data sources'''
    def _publish(self, wfTool, item):
        try:
            wfTool.doActionFor(item, action='publish')
            item.reindexObject()
        except WorkflowException:
            pass
        for i in item.objectIds():
            subItem = item[i]
            self._publish(wfTool, subItem)
    def __call__(self):
        _logger.info('INGEST EVERYTHING FULLY')

        # Turn OFF content rules during ingest
        contentRules = getUtility(IRuleStorage)
        contentRulesState = contentRules.active
        contentRules.active = False

        # Find out what paths to ingest
        context = aq_inner(self.context)
        portalURL = getToolByName(context, 'portal_url')
        portal = portalURL.getPortalObject()
        reportEmail = portal.getProperty('ingestReportEmail', _defaultIngestReportEmail)
        paths = portal.getProperty('edrnIngestPaths', [])
        doNotPublish = portal.getProperty('nonPublishedIngestPaths', _doNotPublish)
        doNotDelete = portal.getProperty('nonClearedIngestPaths', _doNotDelete)
        report = [
            u'The following is a report of the RDF ingest for the EDRN portal at {}:'.format(portalURL())
        ]

        try:
            # No paths?  No need to continue.
            if len(paths) == 0:
                _logger.info("There are no ingest paths, so there's nothing to ingest.")
                report.append(u'There are no ingest paths configured for the portal, so no ingest')
                return

            # We'll need the workflow tool later on.
            wfTool = getToolByName(context, 'portal_workflow')

            # Ignore link integrity checks
            request = aq_inner(self.request)
            getattr(request, 'environ')[ILinkIntegrityInfo(request).getEnvMarker()] = 'all'

            # Ingest and publish each path
            for path in paths:
                try:
                    _logger.info('Starting ingest of "%s"', path)
                    report.append(u'Starting ingest of "{}"'.format(path))
                    obj = portal.restrictedTraverse(path.split('/'))
                    if path not in doNotDelete:
                        obj.manage_delObjects(obj.objectIds())
                    ingestor = getMultiAdapter((obj, self.request), name=u'ingest')
                    ingestor.render = False
                    ingestor()
                    transaction.commit()
                    _logger.info('Ingest of "%s" completed', path)
                    report.append(u'Ingest of "{}" completed'.format(path))
                    # Some paths don't need publication
                    if path not in doNotPublish:
                        self._publish(wfTool, obj)
                        _logger.info('And published all of "%s" too', path)
                        report.append(u'Published everything in "{}"'.format(path))
                    else:
                        _logger.info('Skipping publishing of "%s" since it takes care of its own publication state', path)
                        report.append(u'Skipping publishing of "{}"; it takes care of its own publication'.format(path))
                    transaction.commit()
                except:
                    _logger.exception('Ingest failed for "%s"', path)
                    report.append(u'Ingest failed for "{}"'.format(path))

            # And re-index
            _logger.info('Clearing and rebuilding the catalog')
            report.append(u'Clearing and rebuilding the catalog.')
            catalog = getToolByName(context, 'portal_catalog')
            catalog.clearFindAndRebuild()
            transaction.commit()

            # OK, now we can restore whatever the content rule state was
            contentRules.active = contentRulesState
            _logger.info('All ingestion completed')
            report.append(u'All ingestion completed')
        finally:
            date = unicode(datetime.date.today().isoformat())
            plone.api.portal.send_email(
                recipient=reportEmail,
                subject=u'EDRN Portal Ingest {} for {}'.format(date, portalURL()),
                body=u'\n'.join(report)
            )
