#!/usr/bin/env python
"""
Goal: find out how to efficiently show a list of places
with number of related events for each of them.
"""
from confu import Configurable

from storage import Storage
from models import Entity, Event, Place, Person


class AlgoTest(Configurable):
    needs = {
        'storage': Storage,
    }
    def events_per_place(self):
        Entity._get_root_storage = lambda: self.storage
        places = Place.find()
        #events = Event.find()
        #Event._storage()._ensure_data_ready()
        #yield 'events index:', Event._storage()._index
        #yield 'places index:', Place._storage()._index
        for place in places:
            #yield '{}'.format(place)
            yield '{} ({})'.format(place, len(place.events))
            #yield '{} ({})'.format(place, len(list(place.events_shallow())))


    @property
    def commands(self):
        return [self.events_per_place]
