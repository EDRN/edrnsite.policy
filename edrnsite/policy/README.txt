This package specifies the overall policy for the Plone-based portal for the
Early Detection Research Network, http://edrn.nci.nih.gov.  The purpose of
this policy is, essentially, to turn a regular Plone site into the EDRN public
portal.


Tests
=====

In order to execute these tests, we'll first need a test browser::

    >>> from Products.Five.testbrowser import Browser
    >>> browser = Browser()
    >>> portalURL = self.portal.absolute_url()
        
We also change some settings so that any errors will be reported immediately::

    >>> browser.handleErrors = False
    >>> self.portal.error_log._ignored_exceptions = ()

And finally we'll log in as an administrator::

    >>> from Products.PloneTestCase.setup import portal_owner, default_password
    >>> browser.open(portalURL + '/login_form?came_from=' + portalURL)
    >>> browser.getControl(name='__ac_name').value = portal_owner
    >>> browser.getControl(name='__ac_password').value = default_password
    >>> browser.getControl(name='submit').click()


