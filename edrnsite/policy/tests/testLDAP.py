# encoding: utf-8
# Copyright 2008–2012 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

'''
testLDAP.py

Tests for the LDAP configuration of the EDRN Site policy.
'''

import unittest
from edrnsite.policy.testing import EDRNSITE_POLICY_INTEGRATION_TESTING
from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin, ICredentialsResetPlugin, \
    IGroupEnumerationPlugin, IGroupsPlugin, IPropertiesPlugin, IRoleEnumerationPlugin, IRolesPlugin, IUserAdderPlugin, \
    IUserEnumerationPlugin
from Products.PlonePAS.interfaces.group import IGroupManagement
from Products.PlonePAS.interfaces.plugins import IUserManagement

class LDAPTest(unittest.TestCase):
    '''Unit tests the LDAP configuration of the EDRN site policy.'''
    layer = EDRNSITE_POLICY_INTEGRATION_TESTING
    def setUp(self):
        super(LDAPTest, self).setUp()
        self.portal = self.layer['portal']
    def testLDAPServers(self):
        '''Ensure LDAP servers are declared properly.'''
        # No longer viable under plone.app.testing
        # servers = self.portal.acl_users['ldap-plugin'].acl_users.getServers()
        # self.assertEquals(1, len(servers))
        # server = servers[0]
        # self.assertEquals('cancer.jpl.nasa.gov', server['host'])
        # self.assertEquals(15, server['op_timeout'])
        # self.assertEquals('ldaps', server['protocol'])
        # self.assertEquals('636', server['port'])
        # self.assertEquals(5, server['conn_timeout'])
    def testLDAPSettings(self):
        '''Check if LDAP settings are correct.'''
        # No longer viable under plone.app.testing
        # ldap = self.portal.acl_users['ldap-plugin'].acl_users
        # self.assertEquals('uid', ldap._login_attr)
        # self.assertEquals('uid', ldap._uid_attr)
        # self.assertEquals('uid', ldap._rdnattr)
        # self.assertEquals('dc=edrn,dc=jpl,dc=nasa,dc=gov', ldap.users_base)
        # self.assertEquals(1, ldap.users_scope)
        # self.failIf(ldap._local_groups)
        # self.assertEquals('dc=edrn,dc=jpl,dc=nasa,dc=gov', ldap.groups_base)
        # self.assertEquals(1, ldap.groups_scope)
        # self.failIf(ldap._implicit_mapping)
        # self.assertEquals('uid=admin,ou=system', ldap._binduid)
        # self.assertEquals('70ve4edrn!', ldap._bindpwd)
        # # Ensure the negative cache timeout is zero so that failed logins get counted properly by LoginLockout
        # self.assertEquals(0, ldap.getCacheTimeout('negative'))
    def testForLDAP(self):
        '''Check if the LDAP acl_users is installed.'''
        # No longer viable under plone.app.testing
        # self.failUnless('ldap-plugin' in self.portal.acl_users.keys())
    def testPlugins(self):
        '''Check plugin configuration.'''
        # No longer viable under plone.app.testing
        # pluginRegistry = self.portal.acl_users.plugins
        # for iface in (
        #     IAuthenticationPlugin, ICredentialsResetPlugin, IGroupEnumerationPlugin, IGroupsPlugin, IPropertiesPlugin,
        #     IRoleEnumerationPlugin, IRolesPlugin, IUserAdderPlugin, IUserEnumerationPlugin, IGroupManagement, IUserManagement
        # ):
        #     plugins = [i[0] for i in pluginRegistry.listPlugins(iface)]
        #     self.failUnless('ldap-plugin' in plugins)

def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
