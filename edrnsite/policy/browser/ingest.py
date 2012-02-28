# encoding: utf-8
# Copyright 2010 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

'''EDRN Site Policy: browser capabilities: ingestion.'''

from Acquisition import aq_inner
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.Five.browser import BrowserView
from zope.component import getMultiAdapter, getUtility
from plone.contentrules.engine.interfaces import IRuleStorage
from plone.app.linkintegrity.interfaces import ILinkIntegrityInfo
import logging

_logger = logging.getLogger(__name__)

# These folders set their publication state based on security directives in their
# RDF streams (or in their ingest code), and therefore don't need a manual publication step.
_doNotPublish = ('biomarkers', 'science-data', 'specimens')

# These folders update their contents and require no deletion beforehand
_doNotDelete = ('protocols', 'sites', 'specimens')

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
        portal = getToolByName(context, 'portal_url').getPortalObject()
        paths = portal.getProperty('edrnIngestPaths', [])
        
        # No paths?  No need to continue.
        if len(paths) == 0:
            _logger.info("There are no ingest paths, so there's nothing to ingest.")
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
                obj = portal.restrictedTraverse(path.split('/'))
                if path not in _doNotDelete:
                    obj.manage_delObjects(obj.objectIds())
                ingestor = getMultiAdapter((obj, self.request), name=u'ingest')
                ingestor.render = False
                ingestor()
                _logger.info('Ingest of "%s" completed', path)
                # Some paths don't need publication
                if path not in _doNotPublish:
                    self._publish(wfTool, obj)
                    _logger.info('And published all of "%s" too', path)
                else:
                    _logger.info('Skipping publishing of "%s" since it takes care of its own publication state', path)
            except:
                _logger.exception('Ingest failed for "%s"', path)
        
        # OK, now we can restore whatever the content rule state was
        contentRules.active = contentRulesState
        _logger.info('All ingestion completed')
    

