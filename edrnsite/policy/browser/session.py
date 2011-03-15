# encoding: utf-8
# Copyright 2011 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

from zope.app.component.hooks import getSite
from Products.Five.browser import BrowserView

class SecretGenerator(BrowserView):
    '''
    Generate a new session signing secret.  Workaround for http://dev.plone.org/plone/ticket/8304
    and http://markmail.org/message/ps3mzznxiek6snnz.
    '''
    def __call__(self):
        portal = getSite()
        session = portal.unrestrictedTraverse(('acl_users', 'session'))
        session.source.createNewSecret() # POS
    
