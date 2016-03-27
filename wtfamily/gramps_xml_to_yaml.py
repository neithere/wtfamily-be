#!/usr/bin/env python
"""
Experimental converter of compressed Gramps XML to YAML.

The resulting form is not defined yet.  It depends on the first results.
Perhaps something like a file per object in an entity-specific directory would
be fine.
"""
import datetime
import gzip
import uuid
from xml.etree import ElementTree

import argh
import blessings
from monk import *
import yaml

from models import DateRepresenter, COMMON_SCHEMA, PLACE_SCHEMA, PERSON_SCHEMA


GRAMPS_NAMESPACE_LABEL = 'gramps'
NAMESPACES = {
    #GRAMPS_NAMESPACE_LABEL: 'http://gramps-project.org/xml/1.6.0/',
    GRAMPS_NAMESPACE_LABEL: 'http://gramps-project.org/xml/1.7.1/',
}
PK_FIELD_DEFAULT = 'id'
PK_FIELD_FOR_ENTITY = {
    'gramps:namemaps': 'key',
}

def _with_namespace(field_name):
    return '{' + NAMESPACES[GRAMPS_NAMESPACE_LABEL] + '}' + field_name

def _strip_namespace(field_name):
    return field_name.replace('{' + NAMESPACES[GRAMPS_NAMESPACE_LABEL] + '}', '')

def _strip_namespace_label(entity_name):
    return entity_name.replace(GRAMPS_NAMESPACE_LABEL + ':', '')

GRAMPS_ENTITIES = (
    'gramps:name-formats',
    'gramps:events',
    'gramps:people',
    'gramps:families',
    'gramps:sources',
    'gramps:places',
    'gramps:objects',
    'gramps:repositories',
    'gramps:notes',
    'gramps:bookmarks',
    'gramps:namemaps',
    'gramps:citations',
)
SINGLE_VALUE_FIELDS = (
    # generic
    'id',
    'handle',    # Gramps-specific internal ID
    'change',    # last changed timestamp
    'priv',      # is this a private record?

    'dateval',
    'daterange',
    'datespan',

    # citations
    'sourceref',
    'page',
    'confidence',

    # events
    'description',

    # families
    'father',
    'mother',

    # repositories
    'rname',

    # sources
    'stitle',
    'sauthor',
    'spubinfo',
    'sabbrev',

    # notes
    'text',

    # namemaps
    'type',
    'key',
    'value',


    # places
    'ptitle',
    #'name',     # XXX it can be 1 for place but 1..N for person
    'coord',

    # people
    'gender',

    # people.name
    'first',
    'nick',
    'group',

    # media objects
    'file',
)
SINGLE_VALUE_FIELDS_PER_ENTITY = {
    'gramps:places': ('name',),
}
HLINK_FIELDS = (
    'sourceref',
    'citationref',
    'reporef',
    'placeref',
    'eventref',
    'noteref',
    'objref',
    'personref',
    'place',
    'father',
    'mother',
    'childref',
    'parentin',
    'childof',
)
# fields about which we are *sure* that they *can* have multiple values.
# in the future we may want a strict check and a field will have to belong
# to one of the two mappings.
MULTI_VALUE_FIELDS = (
    # repositories
    'url',
)
assert not any(x in SINGLE_VALUE_FIELDS for x in MULTI_VALUE_FIELDS)


SCHEMATA = {
    'gramps:places': PLACE_SCHEMA,
    'gramps:people': PERSON_SCHEMA,
}
for k in SCHEMATA:
    SCHEMATA[k].update(COMMON_SCHEMA)


t = blessings.Terminal()


def extract(path):
    print('extract...')
    with gzip.open(path) as f:
        root = ElementTree.fromstring(f.read())
    #print(root.tag)
    #print(root.attrib)
    #print(list(root))
    return root


def transform(xml_root):
    print('transform...')
    handle_to_id = {}
    converter = Converter()
    entities = []
    for entity_name in GRAMPS_ENTITIES:
        schema = SCHEMATA.get(entity_name)
        nodes = xml_root.findall(entity_name + '/', NAMESPACES)
        for node in nodes:
            pk, item = converter(node, entity_name=entity_name)
            if schema:
                try:
                    validate(schema, item)
                except ValidationError as e:
                    print(entity_name, pk, item)
                    raise e from None
            if 'handle' in item:
                handle = item['handle']
                handle_to_id[handle] = pk
            entities.append((_strip_namespace_label(entity_name), pk, item))
    for kind, pk, item in entities:
        item_with_pk_links = _replace_hlinks_with_ids(item, handle_to_id)
        yield kind, pk, item_with_pk_links


def load(items, out):
    print('load...')
    full_data = {}
    for entity_name, pk, data in items:
        full_data.setdefault(entity_name, {})[pk] = data

    with open(out, 'w') as f:
        yield yaml.dump(full_data, f, allow_unicode=True,
                        default_flow_style=False)
    print('Wrote YAML to {}'.format(t.yellow(out)))


def main(path='/tmp/all.gramps', out='/tmp/all.gramps.yaml'):
    xml_root = extract(path)
    items = transform(xml_root)
    for x in load(items, out):
        pass


def _replace_hlinks_with_ids(item, handle_to_id):
    item_with_pk_links = {}
    for field_name in item:
        value = item[field_name]
        if field_name in HLINK_FIELDS:
            if field_name in SINGLE_VALUE_FIELDS:
                if 'hlink' in value:
                    handle = value.pop('hlink')
                    value['id'] = handle_to_id[handle]
            else:
                fixed_value = []
                for val in value:
                    if 'hlink' in val:
                        handle = val.pop('hlink')
                        val['id'] = handle_to_id[handle]
                    fixed_value.append(val)
                value = fixed_value

        item_with_pk_links[field_name] = value
    return item_with_pk_links

def _extract_dateval_quality(value):
    quality = value.get('quality')
    mapping = {
        None: DateRepresenter.QUAL_NONE,
        'estimated': DateRepresenter.QUAL_ESTIMATED,
        'calculated': DateRepresenter.QUAL_CALCULATED,
    }
    return mapping[quality]

def _extract_dateval_type(value):
    type_ = value.get('type')
    mapping = {
        None: DateRepresenter.MOD_NONE,
        'before': DateRepresenter.MOD_BEFORE,
        'after': DateRepresenter.MOD_AFTER,
        'about': DateRepresenter.MOD_ABOUT,
    }
    return mapping[type_]

def _normalize_dateval(value):
    d = {
        'quality': _extract_dateval_quality(value),
        'modifier': _extract_dateval_type(value),
        'value': value['val'],
    }
    for k in ('quality', 'modifier'):
        if d[k] is None:
            del d[k]
    return d

def _normalize_datespan(value):
    return _normalize_compound_date(value, DateRepresenter.MOD_SPAN)

def _normalize_daterange(value):
    return _normalize_compound_date(value, DateRepresenter.MOD_RANGE)

def _normalize_compound_date(value, modifier):
    d = {
        'quality': _extract_dateval_quality(value),
        'modifier': modifier,
        'value': {
            'start': value.get('start'),
            'stop': value.get('stop'),
        },
    }
    for k in ('quality',):
        if d[k] is None:
            del d[k]
    return d

def _normalize_bool(value):
    return bool(value)


GLOBAL_FIELD_PROCESSORS = {
    'change': lambda v: datetime.datetime.utcfromtimestamp(int(v)) if v else None,
    'dateval': _normalize_dateval,
    'datespan': _normalize_datespan,
    'daterange': _normalize_daterange,
    'priv': _normalize_bool,
}

GLOBAL_FIELD_RENAME = {
    'dateval': 'date',
    'datespan': 'date',
    'daterange': 'date',
}

# XXX challenges:
# - forward-looking hlink→ID resolver
#   - perhaps as a final step, outside of the converter?
#     it would just register the mappings on an external visitor object)
#     - we'll also need to go *into* the items.  They should be flat-ish, i.e.
#       each item is a dictionary where values can be single or multiple.
#       This is defined by schema.
#       So we just iterate the list if the field isn't in SINGLE_VALUE_FIELDS.
# - some entities (e.g. namemaps) don't have IDs
#   - currently using UUID but not sure if it's ok
class Converter:
    def __init__(self):
        self._handle_to_id = {}

    def __call__(self, node, entity_name=None):
        item = {}
        for k, v in self._get_fields_from_node(node, entity_name):
            field, value = self._normalize_field_name_and_value(k, v,
                                                                entity_name, item)
            item[field] = value

        pk_field = PK_FIELD_FOR_ENTITY.get(entity_name, PK_FIELD_DEFAULT)

        pk = node.attrib.get(pk_field, str(uuid.uuid1()))    # if there's no id, assign a UUID
        handle = node.attrib.get('handle', pk)               # if there's no handle, use ID
        self._alias_handle_to_id(handle, pk)

        return pk, item

    def _normalize_field_name_and_value(self, raw_key, value, entity_name, data_so_far):

        transform = GLOBAL_FIELD_PROCESSORS.get(raw_key)
        if transform:
            value = transform(value)

        field = GLOBAL_FIELD_RENAME.get(raw_key, raw_key)

        # TODO: split another method here

        is_single_value = (
            raw_key in SINGLE_VALUE_FIELDS
            or raw_key in SINGLE_VALUE_FIELDS_PER_ENTITY.get(entity_name, []))
        if is_single_value:
            assert raw_key not in data_so_far
            return field, value
        else:
            existing_value = data_so_far.get(field, [])
            if value:
                return field, existing_value + [value]
            else:
                return field, existing_value

    def _get_fields_from_node(self, entity_node, entity_name):
        """
        :param entity_node: XML tag representing a single entity of given type.
            It can have nested nodes (entity properties/fields) which, in turn,
            can include further levels.

        Simple (single-value) fields are mapped to key/value pairs.
        The values are plain (e.g. a string).

        Complex (nested/multi-value) fields are mapped to key/value pairs
        where the key is the unique name of the fields and the value is a
        list of values this fields takes.  For example, this XML::

            <my_entity attr1="1">
                <foo albatross="2"/>
                <foo albatross="3"/>
                <bar bar_attr="4">abc</bar>
                <quux quux_attr="5">
                    <bingo>Hello</bingo>
                </quux>
            </my_entity>

        ...may map to native Python data structures this way::

            # in a list of "my_entity" items:
            {
                'attr1': '1',
                'foo': [
                    {'albatross': '2'},
                    {'albatross': '3'},
                ],
                'bar': [
                    { 'bar_attr': '4', 'text': 'abc', }
                ],
                'quux': [
                    {
                        'quux_attr': '5',
                        'bingo': ['Hello'],    # or {'text': 'Hello'}
                    }
                ]

            }

        The details may depend on implementation.  See schema.
        """
        for k, v in entity_node.attrib.items():
            yield k, v

        for field_node in entity_node:
            #print(t.blue('  {}  "{}"   {}'.format(child.tag, (child.text or '').strip(), child.attrib)))
            field_name = _strip_namespace(field_node.tag)

            assert not (field_node.attrib and (field_node.text.strip() if field_node.text else None))
            value = field_node.attrib.copy() or field_node.text


            if len(field_node):
                # XXX tag-specific logic
                if entity_name == 'gramps:people' and field_name == 'name':
                    if isinstance(value, str):
                        value = {'text': value}
                    for subfield_node in field_node:
                        complex_fields = 'surname', 'citationref', 'dateval'
                        nested_field = _strip_namespace(subfield_node.tag)

                        if nested_field in complex_fields:
                            nested_value = subfield_node.attrib.copy()
                            if subfield_node.text:
                                nested_value.update(text=subfield_node.text)
                        else:
                            nested_value = subfield_node.text

                        nested_field, nested_value = self._normalize_field_name_and_value(
                            nested_field, nested_value, entity_name, value)

                        if nested_value not in (None, []):
                            value[nested_field] = nested_value
                else:
                    if isinstance(value, str):
                        value = {'text': value}
                    for subfield in field_node:
                        subfield_shortname = _strip_namespace(subfield.tag)
                        subdata = subfield.attrib.copy()
                        value.setdefault(subfield_shortname, []).append(subdata)
                # XXX / tag-specific logic

            # HACK, should be declarative
            if 'priv' in value:
                value['priv'] = bool(value['priv'])

            yield field_name, value


    def _alias_handle_to_id(self, handle, id):
        assert handle not in self._handle_to_id
        self._handle_to_id[handle] = id


if __name__ == '__main__':
    argh.dispatch_command(main)
