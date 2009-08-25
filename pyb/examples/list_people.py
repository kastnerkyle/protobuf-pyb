#! /usr/bin/python

# Adapted from the protobuf examples/ dir

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
#print sys.path
import pyb
from pan.core import json

# Iterates though all people in the AddressBook and prints info about them.
def ListPeople(address_book):
  for person in address_book.person:
    print "Person ID:", person.id
    print "  Name:", person.name
    if 'email' in person:
      print "  E-mail address:", person.email

    for phone_number in person.phone:
      if phone_number.type == addressbook.Person.MOBILE:
        print "  Mobile phone #:",
      elif phone_number.type == addressbook.Person.HOME:
        print "  Home phone #:",
      elif phone_number.type == addressbook.Person.WORK:
        print "  Work phone #:",
      print phone_number.number

# Main procedure:  Reads the entire address book from a file and prints all
#   the information inside.
if len(sys.argv) != 2:
  print "Usage:", sys.argv[0], "ADDRESS_BOOK_FILE"
  sys.exit(-1)

db = pyb.DescriptorSet.FromJsonFile(
    'testdata/addressbook/addressbook.desc.json-from-protoc')
addressbook = db.AllTypes()

# Read the existing address book.
f = open(sys.argv[1], "rb")
encoded = f.read()
print repr(encoded)
address_book = addressbook.AddressBook(encoded)
print address_book
f.close()

ListPeople(address_book)
