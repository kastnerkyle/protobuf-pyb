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
    try:
      return self.__getitem__(attr)
    except KeyError:
      raise AttributeError
