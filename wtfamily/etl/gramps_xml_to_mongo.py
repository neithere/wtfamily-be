#!/usr/bin/env python
#
#    WTFamily is a genealogical software.
#
#    Copyright © 2014—2018  Andrey Mikhaylenko
#
#    This file is part of WTFamily.
#
#    WTFamily is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    WTFamily is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with WTFamily.  If not, see <http://gnu.org/licenses/>.
"""
Converter of (un)compressed Gramps XML to WTFamily MongoDB.
"""
import binascii
import datetime
import gzip
# NOTE: not bundled with Python but separate library; it can pretty-print.
from lxml import etree
import pprint

from models import (Entity, Person, Family, Event, Citation, Source, Place,
                    Repository, MediaObject, Note, Bookmark, NameMap,
                    NameFormat)

import etl.serializers as s


WTFAMILY_APP_NAME = 'WTFamily'
GRAMPS_XML_VERSION_TUPLE = (1, 7, 1) # version for Gramps 4.2
GRAMPS_XML_VERSION = '.'.join(str(i) for i in GRAMPS_XML_VERSION_TUPLE)
GRAMPS_URL_HOMEPAGE = "http://gramps-project.org/"


def extract(path):
    print('Extracting from {} ...'.format(path))

    if _is_gzip_file(path):
        opener = gzip.open
    elif _is_plain_xml_file(path):
        opener = lambda x: open(x, 'rb')
    else:
        raise ValueError('File {} is neither a plain nor a gzipped XML file'
                         .format(path))

    with opener(path) as f:
        xml_root_el = etree.fromstring(f.read())

    return xml_root_el


def _is_gzip_file(path):
    with open(path, 'rb') as f:
        return binascii.hexlify(f.read(2)) == b'1f8b'


def _is_plain_xml_file(path):
    with open(path, 'r') as f:
        return f.read(5) == '<?xml'


def transform(xml_root_el):
    # NOTE: this largerly mirrors/copies the import code; can we unify them?
    model_to_tag = {
        Person: ('people', 'person', s.PersonSerializer),
        Family: ('families', 'family', s.FamilySerializer),
        Event: ('events', 'event', s.EventSerializer),
        Source: ('sources', 'source', s.SourceSerializer),
        Place: ('places', 'placeobj', s.PlaceSerializer),
        MediaObject: ('objects', 'object', s.MediaObjectSerializer),
        Repository: ('repositories', 'repository', s.RepositorySerializer),
        Note: ('notes', 'note', s.NoteSerializer),
        # TODO: Tag: ('tags', 'tag', s.TagSerializer),
        Citation: ('citations', 'citation', s.CitationSerializer),
        Bookmark: ('bookmarks', 'bookmark', s.BookmarkSerializer),
        NameMap: ('namemaps', 'map', s.NameMapSerializer),
        NameFormat: ('name-formats', 'format', s.NameFormatSerializer),
    }
    models = (Person, Family, NameFormat, Event, Citation, Source, Place,
              Repository, MediaObject, Note, Bookmark, NameMap)

    # Gather the mappings of internal Gramps IDs ("handles") to "public" IDs.
    handle_to_id = {}
    for el in xml_root_el.findall('.//*[@handle]'):
        item_handle = el.get('handle')
        item_id = el.get('id')

        handle_to_id[item_handle] = item_id

    def _qn(name):
        return etree.QName(xml_root_el, name).text

    # Now that we have the full mapping, proceed to extract and transform tags
    for model in models:
        print('  * {}'.format(model.__name__))
        group_tag, item_tag, ItemSerializer = model_to_tag[model]
        search_expr = '{}/{}'.format(_qn(group_tag), _qn(item_tag))
        elems = xml_root_el.findall(search_expr)

        for elem in elems:
            serializer = ItemSerializer()
            try:
                data = serializer.from_xml(elem, handle_to_id=handle_to_id)
            except Exception as e:
                tag_ln = etree.QName(elem.tag).localname
                print('=====================================================')
                print()
                print('ERROR transforming (deserializing) {} tag:'.format(tag_ln))
                print(etree.tostring(elem, encoding='unicode', pretty_print=True))

                raise e

            yield elem, model, data


def load(items, db):
    for elem, model, data in items:
        # TODO: can we avoid repeating this?
        model._get_database = lambda: db

        try:
            model(data).save()
        except Exception as e:
            tag_ln = etree.QName(elem.tag).localname
            print('=====================================================')
            print()
            print('ERROR loading (validating and saving) {} tag:'.format(tag_ln))
            print(etree.tostring(elem, encoding='unicode', pretty_print=True))
            pprint.pprint(data)

            raise e


def import_from_xml(path, db):
    extracted = extract(path)
    transformed = transform(extracted)
    loaded = load(transformed, db)
