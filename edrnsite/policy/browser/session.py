# encoding: utf-8
# Copyright 2011 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

from plone.keyring.interfaces import IKeyManager
from Products.Five.browser import BrowserView
from zope.component import getUtility

class SecretGenerator(BrowserView):
    '''
    Generate a new session signing secret.  Workaround for http://dev.plone.org/plone/ticket/8304
    and http://markmail.org/message/ps3mzznxiek6snnz.
    '''
    def __call__(self):
        keyManager = getUtility(IKeyManager)
        keyManager.rotate()
