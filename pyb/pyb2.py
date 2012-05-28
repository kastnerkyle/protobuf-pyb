#!/usr/bin/python
"""
pyb2.py

Better version of pyb where we:

  - Don't care about the "internal Python" interface -- we use dicts; we don't
    use metaclasses to generate Python classes for each message type.
  - Compile the schema into a tree of decoding functions.
  - Lazily decode?  I don't see a need for this now, but it might fall out.


We reuse encoder.py, decoder.py, and wire_format.py from the open source Python
implementation.

Now all we have to do is walk through the descriptor and construct a tree of
decoders.

Then we get the top level one, and call


# Dynamic bootstrapping, done at startup

descriptor_proto = json.load("the meta descriptor as JSON")

meta_desc_set = MakeTypes(descriptor_proto, type_index)

# This is done per message

address_book_desc_bytes = <Load binary descriptor addressbook.desc.encoded>
# decode raw data; FileDescriptorSet is equivalent of the proto file
address_book_proto = meta_desc_set.decode("google.protobuf.FileDescriptorSet",
                                          address_book_desc_bytes)
# Now create encoders and decoders?
address_book_desc = MakeTypes(address_book_proto, type_index)


address_book_bytes = <Load binary descriptor addressbook.desc.encoded>

dict = address_book_desc.decode("address_book.AddressBook, address_book_bytes)



You may only need to encode XOR decode a given message type.

So how about:

# create an object from the data
address_book_desc = DescriptorSet(address_book_proto, type_index)
# get an coder
address_book_e = address_book_desc.GetEncoder("address_book.AddressBook")
address_book_d = address_book_desc.GetDecoder("address_book.AddressBook")

<byte string> = address_book_e.encode({ person: ... })
{ person: ... } = address_book_e.dcode(<byte string>)


from python_message.py:


Encoding loop:


  def _IsPresent(item):
    "Given a (FieldDescriptor, value) tuple from _fields, return true if the
    value should be included in the list returned by ListFields()."

    if item[0].label == _FieldDescriptor.LABEL_REPEATED:
      return bool(item[1])
    elif item[0].cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE:
      return item[1]._is_present_in_parent
    else:
      return True

  def ListFields(self):
    all_fields = [item for item in self._fields.iteritems() if _IsPresent(item)]
    all_fields.sort(key = lambda item: item[0].number)
    return all_fields

  def InternalSerialize(self, write_bytes):
    for field_descriptor, field_value in self.ListFields():
      field_descriptor._encoder(write_bytes, field_value)

Decoding loop:

  local_ReadTag = decoder.ReadTag
  local_SkipField = decoder.SkipField

  # NOTE: These are the objects in decoder.py wrapped in _SimpleDecoder.
  decoders_by_tag = cls._decoders_by_tag

  def InternalParse(self, buffer, pos, end):
    self._Modified()
    field_dict = self._fields
    while pos != end:
      (tag_bytes, new_pos) = local_ReadTag(buffer, pos)
      field_decoder = decoders_by_tag.get(tag_bytes)
      if field_decoder is None:
        new_pos = local_SkipField(buffer, new_pos, end, tag_bytes)
        if new_pos == -1:
          return pos
        pos = new_pos
      else:
        pos = field_decoder(buffer, new_pos, end, self, field_dict)
    return pos

"""

__author__ = 'Andy Chu'


import sys

try:
  import json
except ImportError:
  import simplejson as json

import decoder
import encoder
import type_checkers
print type_checkers


class Error(Exception):
  pass

class DescriptorSet(object):
  def __init__(self, desc_dict):
    """
    desc_dict: Dictinoary representation of the descriptor
    """
    self.desc_dict = desc_dict
    self.type_index = {}
    self.root = IndexTypes(self.desc_dict, self.type_index)

  def GetDecoder(self, message_name):
    """
    message_name: string "package.Type"
                  Could also be "foo.bar.baz.Type"
    """
    return self.root

    type_index = {}
    IndexTypes(self.desc_dict, type_index)
    return type_index

    for f in self.desc_dict['file']:
      for m in f['message_type']:
        name = m['name']
        print name
        if name == 'FieldDescriptorProto':
          #print m['enum_type']
          for t in m['enum_type']:
            enum_name = t['name']
            if enum_name == 'Type':
              value = t['value']
    return 3

  def GetEncoder(self, message_name):
    pass


class Message(object):
  """A record-like object with an associated schema.

  MakeMessageType generates subclasses of this class at runtime.
  """

  _field_names = set()  # A set of names, for quick lookup
  _fields = {}  # Details about the fields, including types
  _fields_by_tag = {}  # Index of fields by tag number
  _repeated = set()



def IndexEnums(enums, root):
  """Given the enum type information, attach it to the Message class."""
  # Like proto2, we ignore the enum type name.  All enums values live in the
  # parent namespace.  This prevents the annoyance of long chains of dotted
  # names.
  for enum_type in enums:
    for value in enum_type['value']:
      root[value['name']] = value['number']


def MakeMessageType(type_name, fields):
  """Given the message type information, return a new subclass of Message."""

  class_attrs = {}

  repeated = set()  # TODO: Benchmark this
  fields_by_tag = {}

  for field in fields:
    fields_by_tag[field['number']] = field

    # Repeated fields are empty by default.
    if field['label'] == 'LABEL_REPEATED':
      repeated.add(field['name'])

    # Fill in defaults as class attributes.  This takes advantage of Python's
    # normal attribute lookup order.
    if 'default_value' in field:
      class_attrs[field['name']] = field['default_value']

  class_attrs.update({
      '_field_names': set(f['name'] for f in fields),
      '_fields': fields,
      '_fields_by_tag': fields_by_tag,
      '_repeated': repeated,  # repeated fields
      })

  return type(str(type_name), (Message,), class_attrs)
      

def IndexMessages(messages, package, name_list, root, type_index):
  """Create a hierarchy of message types, given information from the
  DescriptorSet.
  
  Args:
    messages: A list of dictionaries.  Each should have a 'name' and a list of
       fields.
    package: The proto package.  This is generally irrelevant to the user of the
        API, but still used internally.
    name_list: Stack of names
    root: The type that encloses these type, or the root _ProtoPackage
    type_index: The message types are registered in this "global" index of types
  """
  for message_data in messages:
    type_name = message_data['name']
    names = name_list + [type_name]  # NOTE: Creating a new list!
    full_name = '.'.join(names)

    fields = message_data['field']

    root[type_name] = message_data

    # Populate the type index owned by an instance of DescriptorSet
    key = '.%s.%s' % (package, full_name)
    type_index[key] = message_data

    subtypes = message_data.get('nested_type', [])
    # Recursive call with 'message_type' as the new root
    IndexMessages(subtypes, package, names, root, type_index)
    IndexEnums(message_data.get('enum_type', []), root)


class _ProtoPackage(object):
  """Used to create protobuf namespaces."""


def IndexTypes(descriptor_set, type_index):
  """Make a dict of foo.bar.baz.Type -> DescriptorProto

  Args:
    descriptor_set: A JSON-like dictionary representation of the
       FileDescriptorSet.
    type_index: A type index to populate

  Returns:
    A _ProtoPackage instance
  """
  # Flatten the file structure, and look up types by their fully qualified
  # names
  root = {}

  # TODO: reflect the directory structure of 'file'
  for f in descriptor_set['file']:
    package = f.get('package', '')
    if package:
      subtree = {}
      root[package] = subtree
    else:
      subtree = root
    IndexMessages(f['message_type'], package, [], subtree, type_index)
    IndexEnums(f.get('enum_type', []), subtree)

  #print.pprint(pool.keys())
  return root


def _LoadDescriptorProto():
  f = open('data/descriptor.proto.json')
  d = json.load(f)
  f.close()
  return d


descriptor_proto = _LoadDescriptorProto()
print type(descriptor_proto)
print descriptor_proto.keys()


def main(argv):
  type_index = {}
  
  # TODO: I want to load binary descriptors.  So first load the meta descriptor,
  # and then use that to load a adddressbook.desc.encoded.

  f = open('testdata/addressbook/addressbook.desc.json-from-protoc')
  d = json.load(f)
  IndexTypes(d, type_index)
  print 'INDEX', type_index

  type_index = {}
  IndexTypes(descriptor_proto, type_index)
  print 'INDEX', type_index


if __name__ == '__main__':
  try:
    success = main(sys.argv)
    sys.exit(not success)
  except Error, e:
    print >> sys.stderr, e.args[0]
    sys.exit(1)
