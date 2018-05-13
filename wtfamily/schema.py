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
from bson import ObjectId
import datetime

from monk import (
    ValidationError,
    IsA, Anything, Equals, Any,
    validate, opt_key, optional, one_of,
)


class OptionalKey(object):
    """
    Syntax sugar for better readability of Monk schemata::

        { opt_key('foo'): str }
        { maybe-'foo': str }
    """
    def __sub__(self, other):
        return opt_key(other)

maybe = OptionalKey()


COMMON_SCHEMA = {
    maybe-'_id': ObjectId,      # specific to MongoDB storage backend
    maybe-'handle': str,        # Gramps-specific internal ID
    maybe-'change': datetime.datetime,   # last changed timestamp
    maybe-'priv': False,        # is this a private record?
}
COMMON_SCHEMA_WITH_ID = {
    'id': str,
    **COMMON_SCHEMA
}
ID_OR_HLINK = one_of(['id', 'hlink'])




LIST_OF_IDS = [str]                  # TODO use this (see above)
LIST_OF_IDS = [{ID_OR_HLINK: str}]    # TODO drop this (need ID manager first)
LIST_OF_IDS_WITH_ROLES = [
    {
        ID_OR_HLINK: str,       # TODO ID instead of hlink
        maybe-'role': str,
    }
]
LIST_OF_URLS = [
    {
        'type': str,
        'href': str,
        maybe-'description': str,
    },
]

GRAMPS_DATESTR = {
    'val': str,
}
GRAMPS_DATEVAL = {
    'val': str,
    maybe-'type': one_of(['before', 'after', 'about']),
    maybe-'quality': one_of(['estimated', 'calculated']),
}
GRAMPS_DATESPAN = {
    'start': str,
    'stop': str,
    maybe-'quality': one_of(['estimated', 'calculated']),
}
GRAMPS_DATERANGE = {
    'start': str,
    'stop': str,
    maybe-'quality': one_of(['estimated', 'calculated']),
}
# this is *our* native, not gramps
GRAMPS_DATE_SCHEMA = one_of([GRAMPS_DATEVAL, GRAMPS_DATESPAN, GRAMPS_DATERANGE,
                             GRAMPS_DATESTR])

UNIFIED_DATE_SCHEMA = {
    maybe-'modifier': one_of(['span', 'range', 'before', 'after', 'about']),
    maybe-'value': IsA(str) | {
        'start': str,
        'stop': str,
    },
    maybe-'quality': str,    # TODO: strict enum
    maybe-'type': one_of(['before', 'after', 'about']),
}
GRAMPS_DATE_SCHEMA_MIXIN = {
    maybe-'daterange': dict,
    maybe-'datespan': dict,
    maybe-'dateval': dict,
    maybe-'datestr': dict,
}
MIXED_DATE_SCHEMA_MIXIN = {
    # unified date format
    maybe-'date': UNIFIED_DATE_SCHEMA,

    # Gramps-like date format
    **GRAMPS_DATE_SCHEMA_MIXIN
}

ATTRIBUTE = {
    'type': str,
    'value': str,
    maybe-'citationref': LIST_OF_IDS,
}

GRAMPS_REF_SCHEMA = {
    ID_OR_HLINK: str,
    **MIXED_DATE_SCHEMA_MIXIN,
}
REF_SCHEMA = {
    #ID_OR_HLINK: str,

    'id': str,
    # TODO: REMOVE THIS?
    maybe-'hlink': str,

    **MIXED_DATE_SCHEMA_MIXIN,
}
OBJREF_SCHEMA = {
    ID_OR_HLINK: str,
    maybe-'region': {
        'corner1_y': int,
        'corner2_y': int,
        'corner1_x': int,
        'corner2_x': int,
    },
    maybe-'noteref': [ REF_SCHEMA ],

    # TODO: REMOVE THIS?
    maybe-'hlink': str,
}

URL_SCHEMA = {
    'href': str,
    'type': str,    # TODO enum
    maybe-'description': str,
}
ADDRESS_SCHEMA = {
    # attrs
    maybe-'priv': bool,

    # tags
    maybe-'street': str,
    maybe-'locality': str,
    maybe-'city': str,
    maybe-'county': str,
    maybe-'state': str,
    maybe-'country': str,
    maybe-'postal': str,
    maybe-'phone': str,
    maybe-'noteref': [REF_SCHEMA],
    maybe-'citationref': [REF_SCHEMA],

    **MIXED_DATE_SCHEMA_MIXIN,
}

FAMILY_SCHEMA = {
    maybe-'father': REF_SCHEMA,
    maybe-'mother': REF_SCHEMA,
    maybe-'rel': {
        'type': str
    },
    maybe-'citationref': [REF_SCHEMA],
    maybe-'noteref': [REF_SCHEMA],
    maybe-'childref': [
        {
            'id': str,
            maybe-'citationref': [REF_SCHEMA],
            maybe-'frel': str,    # TODO enum
            maybe-'mrel': str,    # TODO enum
            maybe-'noteref': [REF_SCHEMA],
        }
    ],
    maybe-'eventref': [
        {
            'id': str,
            'role': str,
        }
    ],
    maybe-'attribute': [ATTRIBUTE],
}
#   TYPE_CHOICES = ('City', 'District', 'Region')
PLACE_SCHEMA = {
    maybe-'ptitle': str,
    maybe-'pname': [
        {
            'value': str,
            maybe-'lang': str,

            **MIXED_DATE_SCHEMA_MIXIN,
        },
    ],
    maybe-'coord': {'long': str, 'lat': str},
    #maybe-'alt_name': [str],
    maybe-'change': datetime.datetime,
    'type': str,    # TODO: strict check?
    #'type': one_of(TYPE_CHOICES),
    maybe-'url': LIST_OF_URLS,

    maybe-'placeref': [

        # FIXME fix import script to upgrade data to 'value'
        #       (seen in Place.placeref.dateval.0)
        #REF_SCHEMA
        Any([ REF_SCHEMA, GRAMPS_REF_SCHEMA ]),
    ],
    maybe-'citationref': LIST_OF_IDS,  # TODO LIST_OF_IDS
    maybe-'noteref': LIST_OF_IDS,      # TODO LIST_OF_IDS
}
PERSON_NAME_SCHEMA = {
    'type': str,
    maybe-'first': str,
    maybe-'surname': [
        IsA(str)
        | {
            'text': str,
            maybe-'derivation': str,
            maybe-'prim': bool,       # is primary?
        },
    ],
    maybe-'nick': str,
    maybe-'citationref': LIST_OF_IDS,
    maybe-'priv': bool,
    maybe-'alt': bool,
    maybe-'group': str,    # group as...
    maybe-'group': str,    # an individual namemap

    **MIXED_DATE_SCHEMA_MIXIN,
}
PERSON_SCHEMA = {
    'name': [
        PERSON_NAME_SCHEMA,
    ],
    'gender': one_of(['M', 'F']),

    maybe-'childof': LIST_OF_IDS,   # families
    maybe-'parentin': LIST_OF_IDS,  # families

    maybe-'url': LIST_OF_URLS,
    maybe-'address': [ ADDRESS_SCHEMA ],

    maybe-'change': datetime.datetime,

    maybe-'objref': [ OBJREF_SCHEMA ],
    maybe-'eventref': [
        {
            ID_OR_HLINK: str,
            maybe-'role': str,
            maybe-'attribute': [ ATTRIBUTE ],
        },
    ],
    maybe-'noteref': LIST_OF_IDS,               # TODO LIST_OF_IDS_WITH_ROLES
    maybe-'citationref': LIST_OF_IDS,           # TODO LIST_OF_IDS_WITH_ROLES
    maybe-'personref': [
        {
            'rel': str,    # напр., "крёстный отец"
            ID_OR_HLINK: str,
            maybe-'citationref': LIST_OF_IDS,
        }
    ],
    maybe-'attribute': [ ATTRIBUTE ],
}
SOURCE_SCHEMA = {
    'stitle': str,
    maybe-'spubinfo': str,
    maybe-'sabbrev': str,
    maybe-'sauthor': str,
    maybe-'noteref': [ REF_SCHEMA ],
    maybe-'objref': [ OBJREF_SCHEMA ],
    maybe-'reporef': [ dict ],    # TODO: strict (extended REF_SCHEMA)
}
CITATION_SCHEMA = {
    'sourceref': REF_SCHEMA,
    maybe-'noteref': [REF_SCHEMA],
    maybe-'objref': [OBJREF_SCHEMA],
    maybe-'page': str,
    maybe-'confidence': str,

    **MIXED_DATE_SCHEMA_MIXIN,
}
EVENT_SCHEMA = {
    'type': str,    # TODO enum
    maybe-'place': REF_SCHEMA,
    maybe-'description': str,
    maybe-'citationref': [REF_SCHEMA],
    maybe-'noteref': [REF_SCHEMA],
    maybe-'objref': [OBJREF_SCHEMA],
    maybe-'attribute': [ATTRIBUTE],

    **MIXED_DATE_SCHEMA_MIXIN
}
NOTE_SCHEMA = {
    'text': str,
    'type': str,            # TODO enum
    maybe-'style': list,    # TODO strict? it contains stuff like (char range + font info)
    maybe-'format': bool,
}

# NOTE: this is very special
BOOKMARK_SCHEMA = {
    'target': one_of(['person', 'family', 'event', 'source', 'citation',
                      'place', 'media', 'repository']),
    'hlink': str
}

NAME_MAP_SCHEMA = {
    'type': str,    # TODO enum
    'key': str,
    'value': str,
}
NAME_FORMAT_SCHEMA = {
    'name': str,
    'fmt_str': str,
    'number': str,    # apparently for sorting
    'active': bool,
}
MEDIA_OBJECT_SCHEMA = {
    'file': {
        'checksum': str,
        'description': str,
        'mime': str,
        'src': str,
    },
    maybe-'citationref': [REF_SCHEMA],

    **MIXED_DATE_SCHEMA_MIXIN,
}
REPOSITORY_SCHEMA = {
    'rname': str,
    'type': str,
    maybe-'url': [ URL_SCHEMA ],
    maybe-'address': [ ADDRESS_SCHEMA ],
}


extended_schemata_with_ids = (
    FAMILY_SCHEMA,
    PLACE_SCHEMA,
    EVENT_SCHEMA,
    PERSON_SCHEMA,
    SOURCE_SCHEMA,
    CITATION_SCHEMA,
    NOTE_SCHEMA,
    MEDIA_OBJECT_SCHEMA,
    REPOSITORY_SCHEMA,
)
extended_schemata = (
    NAME_FORMAT_SCHEMA,
    NAME_MAP_SCHEMA,
    BOOKMARK_SCHEMA,
)

for schema in extended_schemata_with_ids:
    schema.update(COMMON_SCHEMA_WITH_ID)

for schema in extended_schemata:
    schema.update(COMMON_SCHEMA)

