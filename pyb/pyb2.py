#!/usr/bin/python
"""
pyb2.py
"""

__author__ = 'Andy Chu'


import sys

try:
  import json
except ImportError:
  import simplejson as json


class Error(Exception):
  pass


class AttrDict(dict):
  def __getattr__(self, attr):
    """Called when the attribute doesn't exist "statically". """
    try:
      return self.__getitem__(attr)
    except KeyError:
      raise AttributeError



def _LoadDescriptorProto():
  f = open('descriptor.proto.json')
  d = json.load(f, object_hook=AttrDict)
  f.close()
  return d

descriptor_proto = _LoadDescriptorProto()
print type(descriptor_proto)
print descriptor_proto.keys()
