#!/usr/bin/env python
# Use to check if wsgi is set up properly
# python dutils/test_wsgi_server [mytwit/]wsgip3[.py]
from __future__ import print_function
from wsgiref.util import setup_testing_defaults
from wsgiref.simple_server import make_server
from os import sys, path
import importlib

try:
    wsgi_file = sys.argv[1]
except IndexError:
    print("usage: python test_wsgi_server.py mytwit/wsgip3.py")
    sys.exit(-1)

if wsgi_file.endswith('.py'):
    wsgi_file = wsgi_file[:-3]

wsgi_file = wsgi_file.replace('/', '.')
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
wsgi = importlib.import_module(wsgi_file)
from wsgi import application 
httpd = make_server('', 8004, application)
httpd.serve_forever()
