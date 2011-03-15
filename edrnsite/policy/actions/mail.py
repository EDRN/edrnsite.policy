# encoding: utf-8
# Copyright 2010 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

'''Mailing action for content rules for the EDRN site policy.'''

from Acquisition import aq_inner
from Products.CMFCore.utils import getToolByName
from plone.app.contentrules.actions.mail import IMailAction, MailAction, MailActionExecutor, MailAddForm, MailEditForm
from Products.CMFPlone import PloneMessageFactory as _
from zope.formlib import form
from zope.interface import implements
import socket, smtplib

_initiatingGroup = u'National Cancer Institute'

class IEDRNMailAction(IMailAction):
    '''EDRN mail action.'''

class EDRNMailAction(MailAction):
    '''EDRN mail action, which is just like the regular Plone mail action, except that it ignores errors when sending mail.
    Also, it sends mail only when it's an NCI staff member who initiated the action.'''
    implements(IEDRNMailAction)
    element = 'edrn.actions.Mail'

class EDRNMailActionExecutor(MailActionExecutor):
    '''Executor that actually sends email (ignoring errors) on behalf of EDRN, and only when it's an NCI staff
    member who initiated the action.'''
    def __call__(self):
        try:
            context = aq_inner(self.context)
            mtool = getToolByName(context, 'portal_membership')
            if mtool.isAnonymousUser():
                # This should never happen unless someone gives Anonymous edit permissions
                return
            gtool = getToolByName(context, 'portal_groups')
            for i in gtool.getGroupsByUserId(mtool.getAuthenticatedMember().getMemberId()):
                if i.getGroupId() == _initiatingGroup:
                    return super(EDRNMailActionExecutor, self).__call__()
            return True
        except (socket.error, smtplib.SMTPException):
            return True

class EDRNMailAddForm(MailAddForm):
    '''Form to show when adding an EDRN mail action.'''
    form_fields = form.FormFields(IEDRNMailAction)
    label = _(u'Add EDRN Mail Action')
    description = _(u'A mail action that sends only when an NCI staffer initiated the action, and ignores transmission errors.')
    form_name = _(u'Configure EDRN element')
    def create(self, data):
        a = EDRNMailAction()
        form.applyChanges(a, self.form_fields, data)
        return a
        
class EDRNMailEditForm(MailEditForm):
    '''Form to show when editing an EDRN mail action.'''
    form_fields = form.FormFields(IEDRNMailAction)
    label = _(u'Edit EDRN Mail Action')
    description = _(u'A mail action for EDRN that ignores transmission errors.')
    form_name = _(u'Configure EDRN element')
