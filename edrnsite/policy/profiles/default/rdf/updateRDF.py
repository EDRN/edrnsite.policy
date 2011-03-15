#!/usr/bin/env python
# encoding: utf-8

'''Update all RDF files from their canonical sources.
'''

import sys, urllib2, tempfile

_longECASURL = 'http://edrn.jpl.nasa.gov/fmprodp3/rdf/dataset?type=ALL&baseUrl=http://edrn.jpl.nasa.gov/ecas/dataset.php'

_sources = {
    'biomarkerorgans.rdf': 'http://edrn.jpl.nasa.gov/bmdb/rdf/biomarkerorgans',
    'biomarkers.rdf':       'http://edrn.jpl.nasa.gov/bmdb/rdf/biomarkers',
    'bmdb-pubs.rdf':        'http://edrn.jpl.nasa.gov/bmdb/rdf/publications',
    'body-systems.rdf':     'http://ginger.fhcrc.org/dmcc/rdf-data/body-systems/rdf',
    'datasets.rdf':         _longECASURL,
    'diseases.rdf':         'http://ginger.fhcrc.org/dmcc/rdf-data/diseases/rdf',
    'dmcc-pubs.rdf':        'http://ginger.fhcrc.org/dmcc/rdf-data/publications/rdf',
    'people.rdf':           'http://ginger.fhcrc.org/dmcc/rdf-data/registered-person/rdf',
    'protocols.rdf':        'http://ginger.fhcrc.org/dmcc/rdf-data/protocols/rdf',
    'resources.rdf':        'http://edrn.jpl.nasa.gov/bmdb/rdf/resources',
    'sites.rdf':            'http://ginger.fhcrc.org/dmcc/rdf-data/sites/rdf',
    'committees.rdf':       'http://ginger.fhcrc.org/dmcc/rdf-data/committees/rdf',
}

def main():
    for destFile, url in _sources.items():
        o, i, c = open(destFile, 'wb'), urllib2.urlopen(url), 0
        print >>sys.stderr, 'Updating', destFile, '…', 
        sys.stderr.flush()
        while True:
            buf = i.read(512)
            size = len(buf)
            if len(buf) == 0:
                break
            c += size
            o.write(buf)
        print >>sys.stderr, c, 'bytes.'
        o.close()
        i.close()

if __name__ == '__main__':
    main()

