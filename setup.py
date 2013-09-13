#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    setup

    Setup Module

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from setuptools import setup
import re
import os
import ConfigParser


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

config = ConfigParser.ConfigParser()
config.readfp(open('tryton.cfg'))
info = dict(config.items('tryton'))
for key in ('depends', 'extras_depend', 'xml'):
    if key in info:
        info[key] = info[key].strip().splitlines()
major_version, minor_version, _ = info.get('version', '0.0.1').split('.', 2)
major_version = int(major_version)
minor_version = int(minor_version)

requires = ['python-amazon-mws']
for dep in info.get('depends', []):
    if not re.match(r'(ir|res|webdav)(\W|$)', dep):
        requires.append('trytond_%s >= %s.%s, < %s.%s' % (
            dep, major_version, minor_version, major_version, minor_version + 1
        ))
requires.append('trytond >= %s.%s, < %s.%s' % (
    major_version, minor_version, major_version, minor_version + 1
))

setup(
    name='trytond_amazon_mws',
    version=info.get('version', '0.0.1'),
    description='Amazon MWS Integration',
    long_description=read('README.md'),
    author='Openlabs Technologies and Consulting P Ltd.',
    url='http://openlabs.co.in/',
    download_url="https://github.com/openlabs/trytond-amazon-mws",
    package_dir={'trytond.modules.amazon_mws': '.'},
    packages=[
        'trytond.modules.amazon_mws',
        'trytond.modules.amazon_mws.tests',
    ],
    package_data={
        'trytond.modules.amazon_mws': info.get('xml', []) + [
            'tryton.cfg', 'view/*.xml'
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Plugins',
        'Framework :: Tryton',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Legal Industry',
        'Intended Audience :: Manufacturing',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Office/Business',
    ],
    license='GPL-3',
    install_requires=requires,
    tests_require=[],
    zip_safe=False,
    entry_points="""
    [trytond.modules]
    amazon_mws = trytond.modules.amazon_mws
    """,
    test_suite='tests',
    test_loader='trytond.test_loader:Loader',
)
