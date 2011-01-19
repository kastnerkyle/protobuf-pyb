#!/usr/bin/python -S
"""pyb.py

See __init__.py for details

TODO: Might want to rename this module
"""

__author__ = 'Andy Chu'


import base64
import codecs
import pprint
import struct
import sys

# This package
import decoding

try:
  from pan.core import json
except ImportError:
  try:
    import simplejson as json  # Third party
  except ImportError:
    import json  # Python 2.6?


class Error(Exception):
  pass


# TODO: May not need this in the final API
class RawMessage(object):
  """A Message with no schema.  Useful for testing."""

  def __init__(self, **items):
    # Doesn't check the schema
    for name, value in items.iteritems():
      setattr(self, name, value)

  def __eq__(self, other):
    # Value comparison.  TODO: is this right?
    return self.__dict__ == other.__dict__

  def __repr__(self):
    attrs = ', '.join(name for name in dir(self) if not name.startswith('_'))
    return '<%s %s>' % (self.__class__.__name__, attrs)


class Message(RawMessage):
  """A record-like object with an associated schema.

  MakeMessageType generates subclasses of this class at runtime.
  """

  _field_names = set()  # A set of names, for quick lookup
  _fields = {}  # Details about the fields, including types
  _fields_by_tag = {}  # Index of fields by tag number
  _repeated = set()

  def __init__(self, *args, **items):
    if args:
      if len(args) == 1:
        decoding.DecodePart(args[0], 0, self.__class__, self)
      else:
        raise TypeError(
            'Message only takes 1 positional argument (got %s)' % args)
    else:
      RawMessage.__init__(self, **items)

  def __contains__(self, name):
    # We want to test if the *instance* has the given attribute.  So we have to
    # use 'in' instead of hasattr, because hasattr is implemented by calling
    # __getattr__, which needs to return defaults.
    return name in self.__dict__

  def __getattr__(self, name):
    # This is called if the attribute doesn't exist "normally".

    if name in self._repeated:
      # For repeated fields, let the person do person.append(Person()), rather
      # than requiring person = [Person()]
      # TODO: Is this worth it?
      new_list = []  # A new list
      setattr(self, name, new_list)
      return new_list
    else:
      raise AttributeError(
          "%r isn't a valid attribute for message type %s" %
          (name, self.__class__.__name__))

  def __setattr__(self, name, value):
    """You're only allowed to set declared fields on Message objects."""
    if name not in self._field_names:
      raise AttributeError(
          "%r isn't a valid attribute for message type %s" %
          (name, self.__class__.__name__))

    # TODO:
    #
    # - Check nested message types.  Check on append too?
    # - Check integers are integers, strings are strings
    # - Check valid enum types
    # - Can I generate PhoneType.WORK enums?  Yes I can, with metaclasses.
    #   - Compare with stock proto2 API 
    self.__dict__[name] = value

  @classmethod
  def FromBytes(cls, s):
    """Construct an instance of this Message from a string of bytes (decode)."""
    return cls()  # TODO

  def ToBytes(self):
    """Encode this Message instance as a string of bytes."""
    return ''  # TODO


def MakeEnums(enums, message_type):
  """Given the enum type information, attach it to the Message class."""
  # Like proto2, we ignore the enum type name.  All enums values live in the
  # parent namespace.  This prevents the annoyance of long chains of dotted
  # names.
  for enum_type in enums:
    for value in enum_type['value']:
      setattr(message_type, value['name'], value['number'])


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
      

def MakeMessageTypes(messages, package, name_list, root, type_index):
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
    message_type = MakeMessageType(full_name, fields) 
    # Attach the subtype to the root type
    setattr(root, type_name, message_type)
    # Populate the type index owned by an instance of DescriptorSet
    key = '.%s.%s' % (package, full_name)
    type_index[key] = message_type
    # Every message type needs the type index, in order to decode its subtypes.
    # (We could technically make an index for each type containing its subtypes,
    # but it's simpler and cheaper to just use a 'global' one everywhere)
    message_type.type_index = type_index

    subtypes = message_data.get('nested_type', [])
    # Recursive call with 'message_type' as the new root
    MakeMessageTypes(subtypes, package, names, message_type, type_index)
    MakeEnums(message_data.get('enum_type', []), message_type)


class _ProtoPackage(object):
  """Used to create protobuf namespaces."""


def MakeTypes(descriptor_set, type_index):
  """Make a tree of Message types.

  Args:
    descriptor_set: A JSON-like dictionary representation of the
       FileDescriptorSet.
    type_index: A type index to populate

  Returns:
    A _ProtoPackage instance
  """
  # Flatten the file structure, and look up types by their fully qualified
  # names
  root = _ProtoPackage()

  # TODO: reflect the directory structure of 'file'
  for f in descriptor_set['file']:
    package = f.get('package', '')
    MakeMessageTypes(f['message_type'], package, [], root, type_index)
    MakeEnums(f.get('enum_type', []), root)

  #print.pprint(pool.keys())
  return root


class DescriptorSet(object):
  """A generic abstraction for a set of descriptors.
  
  This is sort like DescriptorDatabase in the proto2 implementation, but
  "database" has the wrong connotation here.
  """
  def __init__(self, desc_pool=None, desc_set_dict=None):
    self.desc_pool = desc_pool
    self.desc_set_dict = desc_set_dict

    # Index from type names -> Message subclasses
    self.type_index = {}

    # This is initialized the first time you try to make a type
    self.type_tree = None

  @staticmethod
  def FromDescriptorSet(desc_set):
    """
    Construct from FileDescriptorSet in memory (an instance of
    google.protobuf.FileDescriptorSet).
    """
    pass

  @staticmethod
  def FromJson(desc_set_json):
    """Construct from FileDescriptorSet encoded as JSON."""
    # TODO: This isn't really JSON, it's dictionaries
    desc_set_dict = json.loads(desc_set_json)
    return DescriptorSet(desc_set_dict=desc_set_dict)

  @staticmethod
  def FromJsonFile(filename):
    """Construct from FileDescriptorSet encoded as JSON."""
    f = codecs.open(filename, encoding='utf-8')
    contents = f.read()
    f.close()
    return DescriptorSet.FromJson(contents)

  @staticmethod
  def FromBinary(desc_set):
    """Construct from FileDescriptorSet encoded as binary."""
    # TODO: implement this.
    # 1. the FileDescriptorSet should be loaded as JSON/baked as Python with
    # json2py.  One thing that is weird is that you would need enum constants to
    # make them uniform, like TYPE_STRING.
    # 2. then it can be used to decode the descriptor into an object. 
    # 3. then the descriptor can be used to decode a raw message.
    #return DescriptorSet(desc_set_obj=desc_set_obj)

  def Type(self, root):
    """Retrieve a specific type.

    This is actually the same as AllTypes, but looks nicer from the calling
    side.
    """
    return self.AllTypes(root=root)

  def AllTypes(self, root=''):
    """Get a tree of all types, starting at the optional root."""
    if not self.type_tree:
      self.type_tree = MakeTypes(self.desc_set_dict, self.type_index)
    node = self.type_tree
    for part in root.split('.'):
      if part:
        node = getattr(node, part)
    return node


# The descriptor of descriptors is GLOBAL for now
# TODO: Package this data file more nicely

_desc_set = DescriptorSet.FromJsonFile('descriptor.proto.json')
FileDescriptorSet = _desc_set.Type('FileDescriptorSet')


def ToDict(value):
  """
  Convert a nested Message structure to a Python dictionary/list structure.
  """
  if isinstance(value, list):
    return [ToDict(v) for v in value]

  elif isinstance(value, RawMessage):
    result = {}
    for name in value.__dict__:  # Only my own attributes
      # As a convention to avoid serialization, _ means private
      if not name.startswith('_'):
        # TODO: ToDict will grab class attributes too.  Is that OK?
        field_value = getattr(value, name)
        result[name] = ToDict(field_value)
    return result

  else:  # A primitive type
    # NOTE: This doesn't handle enum names, breaks testDecodeAsJson.
    return value


def EncodeJson(message, **json_options):
  """Encode a nested Message structure as JSON.
  
  TODO: Need the descriptor to base64-encode bytes, like protobufs???
  TODO: Have an option to print in order of field number (need the type for
  this.)

  This unfortunately makes the JSON format non-self-describing.
  """
  d = ToDict(message)
  return json.dumps(d, **json_options)
