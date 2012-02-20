# encoding: utf-8
# Copyright 2009–2012 California Institute of Technology. ALL RIGHTS
# RESERVED. U.S. Government Sponsorship acknowledged.

'''EDRN Site Policy: functional and documentation tests.
'''

import doctest
import unittest2 as unittest
from plone.testing import layered
from edrnsite.policy.testing import EDRNSITE_POLICY_FUNCTIONAL_TESTING as LAYER

optionFlags = (doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE | doctest.REPORT_ONLY_FIRST_FAILURE)

def test_suite():
    return unittest.TestSuite([
        layered(doctest.DocFileSuite('README.txt', package='edrnsite.policy', optionflags=optionFlags), LAYER),
    ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
