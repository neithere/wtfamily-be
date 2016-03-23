from datetime import datetime, timedelta
import functools
import re

import babel.dates
from cached_property import cached_property
from flask import g
from dateutil.parser import parse as parse_date
import geopy.distance

# TODO: remove this
import show_people as _dbi


EVENT_TYPE_BIRTH = 'Birth'
EVENT_TYPE_DEATH = 'Death'


def as_list(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        retval = f(*args, **kwargs)
        return list(retval)
    return inner


class Entity:
    entity_name = NotImplemented
    sort_key = None

    def __init__(self, data):
        self._data = data

    def __eq__(self, other):
        if type(self) == type(other) and self.id == other.id:
            return True
        else:
            return False

    def __hash__(self):
        # for `set([p1, p2])` etc.
        return hash('{} {}'.format(type(self), self.id))

    @classmethod
    def _get_root_storage(cls):
        "This can be monkey-patched to avoid Flask's `g`"
        return g.storage

    @classmethod
    def _get_entity_storage(cls):
        entities = cls._get_root_storage()._entities
        return entities[cls.entity_name]

    @classmethod
    def _storage(cls):
        return cls._get_entity_storage()

    @classmethod
    def _find(cls, conditions=None):
        assert cls.entity_name != NotImplemented
        items = cls._storage().find_and_adapt_to_legacy()

        def _filter(xs):
            for p in xs:
                if not conditions:
                    yield cls(p)
                    continue
                for k, v in conditions.items():
                    if not isinstance(v, list):
                        v = [v]
                    if k in p and p[k] in v:
                        yield cls(p)
                        break

        items = _filter(items)
        if cls.sort_key:
            items = sorted(items, key=cls.sort_key)
        return items

    def _find_refs(self, key, model):
        try:
            pks = _extract_refs(self._data[key])
        except KeyError:
            return []
        pks = pks if isinstance(pks, list) else [pks]
        return model.find_by_pks(pks)


    @classmethod
    def references_to(cls, other, indexed=True):
        """
        Returns objects of this class referencing given object.
        """
        other_cls = other.__class__
        assert issubclass(other_cls, Entity)
        key = cls.REFERENCES[other_cls.__name__]
        if indexed:
            for obj in cls.find_by_index(key, other.id):
                yield obj
        else:
            for obj in cls.find():
                refs = _extract_ids(obj, key)
                if other.id in refs:
                    yield obj

    @classmethod
    def get(cls, pk):
        data = cls._storage().get(pk)
        return cls(data)

    @classmethod
    def find(cls, conditions=None):
        return cls._find(conditions)

    @classmethod
    def find_one(cls, conditions=None):
        for p in cls.find(conditions):
            return p

    @classmethod
    def find_by_pks(cls, pks):
        for pk in pks:
            yield cls.get(pk)

    @classmethod
    def find_by_event_ref(cls, pk):
        # anything except Event can reference to an Event
        for obj in cls.find():
            refs = obj._data.get('eventref')
            if not refs:
                continue
            if pk in _extract_refs(refs):
                yield obj

    @classmethod
    def find_by_index(cls, key, value):
        for item in cls._storage().find_by_index(key, value):
            yield cls(item)

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
            pk = self._data[key]['id']
        except KeyError:
            return None
        else:
            return Person.find_one({'id': pk})

    @property
    def father(self):
        return self._get_participant('father')

    @property
    def mother(self):
        return self._get_participant('mother')

    @property
    def children(self):
        return self._find_refs('childref', Person)

    @property
    def events(self):
        return self._find_refs('eventref', Event)

    @property
    def people(self):
        if self.father:
            yield self.father
        if self.mother:
            yield self.mother
        for child in self.children:
            yield child

    def get_partner_for(self, person):
        assert person in (self.father, self.mother)
        if person != self.father:
            return self.father
        else:
            return self.mother


class Person(Entity):
    entity_name = 'people'
    REFERENCES = {
        'Citation': 'citationref.id',
    }
    NAME_TEMPLATE = '{first} {patronymic} {primary} ({nonpatronymic})'

    # these are for templates, etc.
    GENDER_MALE = 'M'
    GENDER_FEMALE = 'F'

    def __repr__(self):
        #return 'Person {} {}'.format(self.name, self._data)
        return '{}'.format(self.name)

    def _format_all_names(self, template=NAME_TEMPLATE):
        names = self._data['name']
        return _dbi._format_names(names, template) or []

    def _format_one_name(self, template=NAME_TEMPLATE):
        return self._format_all_names(template)[0]

    @property
    def names(self):
        return self._format_all_names()

    @property
    def name(self):
        return self._format_one_name()

    @property
    def first_and_last_names(self):
        return self._format_one_name('{first} {primary}')

    @property
    def first_name(self):
        return self._format_one_name('{first}')

    @property
    def initials(self):
        return ''.join(x[0].upper() for x in self.name.split(' ') if x)

    @property
    def group_names(self):
        name_nodes = self._data['name']
        if not isinstance(name_nodes, list):
            name_nodes = [name_nodes]

        # Check for name groups and aliases; if none, use first found surname
        first_found_surname = None
        for n in name_nodes:
            assert not isinstance(n, str)
            if 'group' in n:
                yield n['group']

            _, primary_surnames, _, _ = _dbi._get_name_parts(n)
            for surname in primary_surnames:
                if not first_found_surname:
                    first_found_surname = surname
                alias = NameMap.group_as(surname)
                if alias:
                    yield alias
        if first_found_surname:
            yield first_found_surname

    @property
    def group_name(self):
        for name in self.group_names:
            # first found wins
            return name
        else:
            return self.name

    @cached_property
    @as_list
    def events(self):
        # TODO: the `eventref` records are dicts with `hlink` and `role`.
        #       we need to somehow decorate(?) the yielded event with these roles.
        events = self._find_refs('eventref', Event)
        return sorted(events, key=lambda e: e.date)

    @cached_property
    @as_list
    def places(self):
        # unique with respect to the original order (expecting events sorted by date)
        places = []
        seen = {}
        for event in self.events:
            if event.place and event.place.id not in seen:
                places.append(event.place)
                seen[event.place.id] = True
        return places

    @property
    def attributes(self):
        try:
            attribs = self._data['attribute']
        except KeyError:
            return []
        return attribs

    @property
    def citations(self):
        return self._find_refs('citationref', Citation)

    def get_parent_families(self):
        return self._find_refs('childof', Family)

    def get_families(self):
        return self._find_refs('parentin', Family)

    def get_parents(self):
        for family in self.get_parent_families():
            if family.mother:
                yield family.mother
            if family.father:
                yield family.father

    def get_siblings(self):
        for family in self.get_parent_families():
            for child in family.children:
                if child != self:
                    yield child

    def get_partners(self):
        for family in self.get_families():
            partners = family.father, family.mother
            for partner in partners:
                if partner and partner != self:
                    yield partner

    def get_children(self):
        for family in self.get_families():
            for child in family.children:
                yield child

    def find_ancestors(self):
        stack = [self]
        while stack:
            p = stack.pop()
            yield p
            for parent in p.get_parents():
                stack.append(parent)

    def find_descendants(self):
        stack = [self]
        while stack:
            p = stack.pop()
            yield p
            for child in p.get_children():
                stack.append(child)

    @cached_property
    @as_list
    def related_people(self):
        parents = list(self.get_parents())
        siblings = list(self.get_siblings())
        partners = list(self.get_partners())
        children = list(self.get_children())
        people = parents + siblings + partners + children
        seen = {}
        for person in people:
            if person.id not in seen:
                yield person
                seen[person.id] = True

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
    def age(self):
        if not self.birth:
            return
        if self.death:
            return self.death.year - self.birth.year
        else:
            return datetime.date.today().year - self.birth.year

    @property
    def gender(self):
        return self._data['gender']

    @property
    def is_male(self):
        return self.gender == self.GENDER_MALE

    @property
    def is_female(self):
        return self.gender == self.GENDER_FEMALE


class Event(Entity):
    entity_name = 'events'
    sort_key = lambda item: item.date
    REFERENCES = {
        'Place': 'place.id',
        'Citation': 'citationref.id',
    }

    def __repr__(self):
        #return 'Event {}'.format(self._data)
        return 'Event {0.date} {0.type} {0.summary} {0.place}'.format(self)

    @property
    def type(self):
        return self._data['type']

    @property
    def date(self):
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
        refs = list(self._find_refs('place', Place))
        if refs:
            assert len(refs) == 1
            return refs[0]

    @property
    def people(self):
        return Person.find_by_event_ref(self.id)

    @property
    def families(self):
        return Family.find_by_event_ref(self.id)

    @property
    def citations(self):
        return self._find_refs('citationref', Citation)

    @classmethod
    def find(cls, conditions=None):
        for elem in cls._find(conditions):
            # exclude orphaned events (e.g. if the person was skipped
            # on export for whatever reason)
            # XXX this may do a big Person query for each event
            if list(elem.people):
                yield elem


class Place(Entity):
    entity_name = 'places'
    REFERENCES = {
        'Citation': 'citationref.id',
    }

    def __repr__(self):
        return '{0.name}'.format(self)

    @property
    def name(self):
        return self.names[0]

    @property
    def names(self):
        return [x['value'] for x in self.names_annotated]

    @property
    def names_annotated(self):
        names = self._data.get('pname', [])
        assert names, 'id={} : {}'.format(self.id, self._data)
        return names

    @property
    def title(self):
        return self._data.get('ptitle')

    @property
    def alt_names(self):
        return self.names[1:]

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
    def coords_tuple(self):
        coords = self.coords
        if not coords:
            return
        return coords['lat'], coords['lng']

    def distance_to(self, other):
        if not (self.coords and other.coords):
            return
        return geopy.distance.vincenty(self.coords_tuple, other.coords_tuple)

    @property
    def parent_places(self):
        return self._find_refs('placeref', Place)

    #@property
    @cached_property
    @as_list
    def nested_places(self):
        for place in self.find_by_index('placeref.id', self.id):
            yield place

    @cached_property
    @as_list
    def events(self):
        for event in Event.references_to(self):
            yield event

    @cached_property
    def events_years(self):
        dates = sorted(e.date for e in self.events if e.date)
        if not dates:
            return 'years unknown'
        since = min(dates)
        until = max(dates)
        if since == until:
            return since
        else:
            return '{.year}—{.year}'.format(since, until)

    @cached_property
    @as_list
    def events_recursive(self):

        # build a list of refs for current place hierarchy
        places = []
        nested_to_see = [self]
        while nested_to_see:
            place = nested_to_see.pop()
            places.append(place)
            nested_to_see.extend(place.nested_places)

        events_seen = {}

        # find events with references to any of these places
        for place in places:
            for event in Event.references_to(place):
                if event.id in events_seen:
                    continue
                yield event
                events_seen[event.id] = True

    @cached_property
    @as_list
    def people(self):
        people = {}
        for event in self.events:
            for person in event.people:
                people.setdefault(person.id, person)
            for family in event.families:
                for person in family.people:
                    people.setdefault(person.id, person)
        return people.values()

#    @classmethod
#    def find(cls, conditions=None):
#        for elem in cls._find(conditions):
#            # exclude orphaned events (e.g. if the person was skipped
#            # on export for whatever reason)
#            if list(elem.people):
#                yield elem


class Source(Entity):
    entity_name = 'sources'
    sort_key = lambda item: item.title

    def __repr__(self):
        return str(self.title)

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
    def abbrev(self):
        return self._data.get('sabbrev')

    @property
    def citations(self):
        return Citation.references_to(self)

    @property
    def repository(self):
        return '(Repository {})'.format(self._data.get('reporef'))


class Citation(Entity):
    entity_name = 'citations'

    REFERENCES = {
        'Source': 'sourceref.id',
    }

    def __repr__(self):
        if self.page:
            return self.page
        return str(self.id)

    @property
    def source(self):
        refs = list(self._find_refs('sourceref', Source))
        if refs:
            assert len(refs) == 1
            return refs[0]

    @property
    def page(self):
        return self._data.get('page')

    @property
    def date(self):
        date = self._data.get('date')
        if date:
            return DateRepresenter(**date)
        else:
            # XXX this is a hack for `xs|sort(attribute='x')` Jinja filter
            # in Python 3.x environment where None can't be compared
            # to anything (i.e. TypeError is raised).
            return DateRepresenter()

    @property
    def notes(self):
        return self._find_refs('noteref', Note)

    @property
    def events(self):
        return Event.references_to(self)

    @property
    def people(self):
        return Person.references_to(self)


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


def _extract_refs(ref):
    """
    Returns a list of IDs (strings)
    """
    if isinstance(ref, str):
        # 'foo'
        return [ref]
    if isinstance(ref, dict):
        # {'hlink': 'foo'}
        return [ref['id']]

    # [{'hlink': 'foo'}]
    assert isinstance(ref, list)

    return [x['id'] if isinstance(x, dict) else x for x in ref]

def _extract_ids(obj, key):
    value = obj._data.get(key)
    if not value:
        return []
    return _extract_refs(value)

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
        return self._format(self.value)

    def _format(self, value):
        formats = {
            self.MOD_NONE: '{}',
            self.MOD_SPAN: '{0[start]}..{0[stop]}',
            self.MOD_RANGE: '[{0[start]}/{0[stop]}]',
            self.MOD_BEFORE: '<{}',
            self.MOD_AFTER: '{}+',
            self.MOD_ABOUT: '≈{}',
        }
        template = formats[self.modifier]
        val = template.format(value)

        quality_abbrevs = {
            self.QUAL_ESTIMATED: 'est',
            self.QUAL_CALCULATED: 'calc',
            self.QUAL_NONE: '',
        }

        vals = [
            quality_abbrevs[self.quality],
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
            value = self.value
        elif self.modifier in self.COMPOUND_MODIFIERS:
            value = self.value.get('start')
        else:
            return ''
        return self._parse_to_year(value)

    @property
    def year_formatted(self):
        if self.is_compound:
            start, stop = self.boundaries
            # match the structure expected by template
            value = {
                'start': self._parse_to_year(start) if start else '',
                'stop':  self._parse_to_year(stop)  if stop  else '',
            }
        else:
            value = self.year
        return self._format(value)

    @property
    def is_estimated(self):
        return self.quality == self.QUAL_ESTIMATED

    @property
    def is_compound(self):
        return self.modifier in self.COMPOUND_MODIFIERS

    @property
    def is_approximate(self):
        return self.is_estimated or self.modifier == self.MOD_RANGE

    @property
    def boundaries(self):
        assert self.is_compound
        return self.value.get('start'), self.value.get('stop')

    @property
    def delta(self):
        if self.modifier == self.MOD_SPAN:
            start, stop = (self._parse_to_datetime(x) for x in self.boundaries)
            assert start and stop
            # TODO format properly for humans
            return stop - start

    @property
    def earliest_datetime(self):
        if self.is_compound:
            value = self.boundaries[0]
        else:
            value = self.value
        return self._parse_to_datetime(value)

    @property
    def latest_datetime(self):
        if self.is_compound:
            value = self.boundaries[-1]
        else:
            value = self.value
        return self._parse_to_datetime(value)

    def delta_compared(self, other):
        return self.earliest_datetime - other.latest_datetime

    def _parse_to_datetime(self, value):
        if isinstance(value, int):
            return datetime(value)
        if not isinstance(value, str):
            raise TypeError('expected a str, got {!r}'.format(value))
        # supplying default to avoid bug when the default day (31) was out
        # of range for given month (e.g. 30th is the last possible DoM).
        #print('    parse_date(', repr(value),')')
        return parse_date(value, default=datetime(1,1,1))

    def _parse_to_year(self, value):
        return self._parse_to_datetime(value).year
