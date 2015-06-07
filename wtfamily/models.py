import re

from flask import g
from dateutil.parser import parse as parse_date

# TODO: remove this
import show_people as _dbi


EVENT_TYPE_BIRTH = 'Birth'
EVENT_TYPE_DEATH = 'Death'


class Entity:
    entity_name = NotImplemented
    sort_key = None

    def __init__(self, data):
        self._data = data

    @classmethod
    def _find(cls, conditions=None):
        assert cls.entity_name != NotImplemented
        entities = g.storage._entities
        entity = entities[cls.entity_name]
        items = entity.find_and_adapt_to_legacy()


        if cls.sort_key:
            items = sorted(items, key=cls.sort_key)
        for p in items:
            if not conditions:
                yield cls(p)
                continue
            for k, v in conditions.items():
                if not isinstance(v, list):
                    v = [v]
                if k in p and p[k] in v:
                    yield cls(p)
                    break

    @classmethod
    def find(cls, conditions=None):
        return cls._find(conditions)

    @classmethod
    def find_one(cls, conditions=None):
        for p in cls.find(conditions):
            return p

    @classmethod
    def find_by_event_ref(cls, hlink):
        # anything except Event can reference to an Event
        for obj in cls.find():
            refs = obj._data.get('eventref')
            if not refs:
                continue
            if hlink in _extract_hlinks(refs):
                yield obj

    @property
    def id(self):
        return self._data['id']

    @property
    def handle(self):
        return self._data['handle']


class Family(Entity):
    entity_name = 'families'

    def __repr__(self):
        return '{} + {}'.format(self.father or '?',
                                self.mother or '?')

    def _get_participant(self, key):
        try:
            hlink = self._data[key]['hlink']
        except KeyError:
            return None
        else:
            return Person.find_one({'handle': hlink})

    @property
    def father(self):
        return self._get_participant('father')

    @property
    def mother(self):
        return self._get_participant('mother')

    @property
    def children(self):
        try:
            hlinks = _extract_hlinks(self._data['childref'])
        except KeyError:
            return []
        return Person.find({'handle': hlinks})

    @property
    def events(self):
        try:
            hlinks = _extract_hlinks(self._data['eventref'])
        except KeyError:
            return []
        return Event.find({'handle': hlinks})


class Person(Entity):
    entity_name = 'people'

    def __repr__(self):
        #return 'Person {} {}'.format(self.name, self._data)
        return '{}'.format(self.name)

    @property
    def name(self):
        return _dbi._format_names(self._data['name'])[0]

    @property
    def names(self):
        return _dbi._format_names(self._data['name'])

    @property
    def group_name(self):
        name_nodes = self._data['name']
        if not isinstance(name_nodes, list):
            name_nodes = [name_nodes]
        for n in name_nodes:
            assert not isinstance(n, str)
            if 'group' in n:
                return n['group']

            _, primary_surnames, _, _ = _dbi._get_name_parts(n)
            for surname in primary_surnames:
                alias = NameMap.group_as(surname)
                if alias:
                    return alias
        return self.name

    @property
    def events(self):
        # TODO: the `eventref` records are dicts with `hlink` and `role`.
        #       we need to somehow decorate(?) the yielded event with these roles.
        try:
            hlinks = _extract_hlinks(self._data['eventref'])
        except KeyError:
            return []
        return Event.find({'handle': hlinks})

    @property
    def attributes(self):
        try:
            attribs = self._data['attribute']
        except KeyError:
            return []
        attribs = _dbi._ensure_list(attribs)
        return attribs

    def get_parent_families(self):
        try:
            hlinks = _extract_hlinks(self._data['childof'])
        except KeyError:
            return []
        return Family.find({'handle': hlinks})

    def get_families(self):
        try:
            hlinks = _extract_hlinks(self._data['parentin'])
        except KeyError:
            return []
        return Family.find({'handle': hlinks})

    def get_parents(self):
        for family in self.get_parent_families():
            if family.mother:
                yield family.mother
            if family.father:
                yield family.father

    @property
    def birth(self):
        for event in self.events:
            if event.type == EVENT_TYPE_BIRTH:
                return event.date
        return DateRepresenter()

    @property
    def death(self):
        for event in self.events:
            if event.type == EVENT_TYPE_DEATH:
                return event.date
        return DateRepresenter()

    @property
    def gender(self):
        return self._data['gender']


class Event(Entity):
    entity_name = 'events'
    sort_key = lambda item: (
        item.get('dateval', {}).get('val', '') or
        item.get('datespan', {}).get('start', '') or
        item.get('daterange', {}).get('start', '')
    )

    def __repr__(self):
        #return 'Event {}'.format(self._data)
        return 'Event {0.date} {0.type} {0.summary} {0.place}'.format(self)

    @property
    def type(self):
        return self._data['type']

    @property
    def date(self):
        #return _dbi._format_dateval(self._data.get('dateval'))
        date = self._data.get('date')
        if date:
            return DateRepresenter(**date)
        else:
            # XXX this is a hack for `xs|sort(attribute='x')` Jinja filter
            # in Python 3.x environment where None can't be compared
            # to anything (i.e. TypeError is raised).
            return DateRepresenter()

    @property
    def summary(self):
        return self._data.get('description', '')

    @property
    def place(self):
        try:
            hlinks = _extract_hlinks(self._data['place'])
        except KeyError:
            return
        return Place.find_one({'handle': hlinks})

    @property
    def people(self):
        return Person.find_by_event_ref(self.handle)

    @property
    def families(self):
        return Family.find_by_event_ref(self.handle)

    @property
    def citations(self):
        try:
            hlinks = _extract_hlinks(self._data['citationref'])
        except KeyError:
            return
        return Citation.find({'handle': hlinks})

    @classmethod
    def find(cls, conditions=None):
        for elem in cls._find(conditions):
            # exclude orphaned events (e.g. if the person was skipped
            # on export for whatever reason)
            if list(elem.people):
                yield elem


class Place(Entity):
    entity_name = 'places'

    def __repr__(self):
        return '{0.title}'.format(self)

    @property
    def name(self):
        return self._data.get('name')

    @property
    def title(self):
        return self._data.get('ptitle')

    @property
    def alt_name(self):
        return _dbi._ensure_list(self._data.get('alt_name', []))

    @property
    def coords(self):
        coords = self._data.get('coord')
        if not coords:
            return
        return {
            'lat': _normalize_coords_to_pure_degrees(coords['lat']),
            'lng': _normalize_coords_to_pure_degrees(coords['long']),
        }

    @property
    def parent_places(self):
        try:
            hlinks = _extract_hlinks(self._data['placeref'])
        except KeyError:
            return
        return Place.find({'handle': hlinks})

    @property
    def nested_places(self):
        #print( {'placeref': {'hlink': self.handle}})
        for place in Place.find():
            if 'placeref' not in place._data:
                continue
            if self.handle in _extract_hlinks(place._data.get('placeref', [])):
                yield place

    @property
    def events(self):
        hlinks = []
        nested_to_see = [self]
        while nested_to_see:
            place = nested_to_see.pop()
            hlinks.append(place.handle)
            nested_to_see.extend(place.nested_places)

        for event in Event.find():
            if event.place and event.place.handle in hlinks:
                yield event

#    @classmethod
#    def find(cls, conditions=None):
#        for elem in cls._find(conditions):
#            # exclude orphaned events (e.g. if the person was skipped
#            # on export for whatever reason)
#            if list(elem.people):
#                yield elem


class Source(Entity):
    entity_name = 'sources'
    sort_key = lambda item: item['stitle'] or ''

    @property
    def title(self):
        return self._data.get('stitle')

    @property
    def author(self):
        return self._data.get('sauthor')

    @property
    def pubinfo(self):
        return self._data.get('spubinfo')

    @property
    def citations(self):
        for citation in Citation.find():
            if self.handle in _extract_hlinks(citation._data.get('sourceref')):
                yield citation


class Citation(Entity):
    entity_name = 'citations'

    def __repr__(self):
        return str(self.id)

    @property
    def source(self):
        return Source.find_one({'handle': self._data['sourceref']['hlink']})

    @property
    def page(self):
        return self._data.get('page')

    @property
    def date(self):
        date = self._data.get('date')
        if date:
            return DateRepresenter(**date)

    @property
    def notes(self):
        try:
            hlinks = _extract_hlinks(self._data['noteref'])
        except KeyError:
            return
        for note in Note.find():
            if note.handle in hlinks:
                yield note

    @property
    def events(self):
        for event in Event.find():
            ref = event._data.get('citationref')
            if not ref:
                continue
            if self.handle in _extract_hlinks(ref):
                yield event


class Note(Entity):
    entity_name = 'notes'

    @property
    def text(self):
        return self._data['text']


class NameMap(Entity):
    entity_name = 'namemaps'

    @property
    def type(self):
        return self._data.get('type')

    @property
    def key(self):
        return self._data.get('key')

    @property
    def value(self):
        return self._data.get('value')

    @classmethod
    def group_as(self, key):
        for item in self.find():
            if item.type == 'group_as' and item.key == key:
                return item.value


class NameFormat(Entity):
    entity_name = 'name-formats'


class MediaObject(Entity):
    entity_name = 'objects'


def _extract_hlinks(ref):
    if isinstance(ref, str):
        # 'foo'
        ref = {'hlink': ref}
    if isinstance(ref, dict):
        # {'hlink': 'foo'}
        ref = [ref]

    # [{'hlink': 'foo'}]
    assert isinstance(ref, list)

    return [x['hlink'] for x in ref]


def _format_date(obj_data):
    date = obj_data.get('date')
    if date:
        return str(DateRepresenter(**date))
    return ''


def _normalize_coords_to_pure_degrees(coords):
    if isinstance(coords, float):
        return coords
    assert isinstance(coords, str)
    parts = [float(x) for x in re.findall('([0-9\.]+)', coords)]
    pure_degrees = parts.pop(0)
    if parts:
        # minutes
        pure_degrees += parts.pop(0) / 60
    if parts:
        # seconds
        pure_degrees += parts.pop(0) / (60*60)
    assert not parts, (coords, pure_degrees, parts)
    if 'S' in coords or 'W' in coords:
        pure_degrees = -pure_degrees
    return pure_degrees


class DateRepresenter:
    """
    A simple alternative to Gramps' gen.lib.date.Date object.

    Supported properties: modifier, quality.

    Unsupported: alternate calendars; newyear start date.

    Examples::

        DateRepresenter()      # unknown/undefined date
        DateRepresenter('1919')

    """
    MOD_NONE = None
    MOD_BEFORE = 'before'
    MOD_AFTER = 'after'
    MOD_ABOUT = 'about'
    MOD_RANGE = 'range'
    MOD_SPAN = 'span'
    MOD_TEXTONLY = 'textonly'
    MODIFIER_OPTIONS = (MOD_NONE, MOD_BEFORE, MOD_AFTER, MOD_ABOUT, MOD_RANGE,
                        MOD_SPAN, MOD_TEXTONLY)
    COMPOUND_MODIFIERS = MOD_RANGE, MOD_SPAN

    QUAL_NONE = None
    QUAL_ESTIMATED = 'estimated'
    QUAL_CALCULATED = 'calculated'
    QUALITY_OPTIONS = (QUAL_NONE, QUAL_ESTIMATED, QUAL_CALCULATED)

    def __init__(self, value=None, modifier=MOD_NONE, quality=QUAL_NONE):
        assert modifier in self.MODIFIER_OPTIONS
        assert quality in self.QUALITY_OPTIONS

        # TODO: validate the arguments

        self.value = value
        self.modifier = modifier
        self.quality = quality

    def __bool__(self):
        return self.value is not None

    def __str__(self):
        if self.value is None:
            return '?'

        formats = {
            self.MOD_NONE: '{}',
            self.MOD_SPAN: '{0[start]}..{0[stop]}',
            self.MOD_RANGE: '{0[start]}-{0[stop]}',
            self.MOD_BEFORE: '<{}',
            self.MOD_AFTER: '{}+',
            self.MOD_ABOUT: '≈{}',
        }
        template = formats[self.modifier]
        val = template.format(self.value)

        vals = [
            self.quality,
            #self.modifier,    # excluded here because it's in the val's template
            val,
        ]
        return ' '.join([x for x in vals if x])

    def __eq__(self, other):
        if isinstance(other, type(self)) and str(self) == str(other):
            return True

    def __lt__(self, other):
        assert isinstance(other, type(self));
        # FIXME this is extremely rough
        return str(self.year) < str(other.year)

    @property
    def century(self):
        year = str(self.year)
        if not year:
            return '?'
        return '{}xx'.format(year[:2])

    @property
    def year(self):
        "Returns earliest known year as string"
        if isinstance(self.value, str):
            return parse_date(self.value).year
        elif self.modifier in self.COMPOUND_MODIFIERS:
            return parse_date(self.value.get('start')).year
        else:
            return ''

    @property
    def is_estimated(self):
        return self.quality == self.QUAL_ESTIMATED
