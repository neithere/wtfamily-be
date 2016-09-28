define([
    'lodash',
    'can/list',
    'can/map',
    'can/model',
    'app/models/person',
    'app/models/place'
], function(_, canList, canMap, Model, Person, Place) {
    var Event = Model({
        findAll: 'GET /r/events/',
        findOne: 'GET /r/events/{id}',
        findWithRelated: function(params) {
            return this.findAll(params).then(function(events) {
                return _.map(events, function(event) {
                    var placeQuery;
                    var personQuery = Person.findAll({by_event: event.id});

                    event.people = new can.List(personQuery);

                    if (!_.isEmpty(event.place_id)) {
                        console.log('finding place by id=', event.place_id);
                        placeQuery = Place.findOne({id: event.place_id});
                        event.place = new can.List(placeQuery);
                        //event.place = placeQuery;
                        //event.place = placeQuery.promise();
                        //event.place.done(function(x){console.log('GOT place', x)});
                        //event.place = new can.Map(placeQuery);
                        //placeQuery.done(function(place) {
                        //    event.place = place;
                        //});
                    }

                    console.log(event);

                    return event;
                });
            });
        },
    }, {});

    return Event;
});
