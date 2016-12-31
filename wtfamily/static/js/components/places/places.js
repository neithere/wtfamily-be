define([
    'app/models/place',
    'app/models/event',
    'can/component',
    'can/map',
    'can/map/define',
    'can/view/mustache',
    'can/route'
], function(Place, Event) {
    var PlaceViewModel = can.Map.extend({
        zoom: 13,
        selectedObject: null,
        filterQuery: null,
        map: null,
        define: {
            object_list: {
                get: function() {
                    var query = this.attr('filterQuery');
                    return Place.findAllSorted({
                        q: query
                    }).done(function(results) {
                        // select on of them according to the active route
                        var objId = can.route.attr('objId');
                        var obj;
                        if (_.isEmpty(objId)) {
                            return null;
                        }
                        obj = _.find(results, {id: objId});
                        this.attr('selectedObject', obj);
                    }.bind(this));
                },
            },
            relatedEvents: {
                get: function() {
                    var place = this.attr('selectedObject');
                    return Event.findWithRelatedByPlaceId(place.id);
                }
            }
        },
        selectObject: function(obj, elems, event) {
            can.route.attr('objId', obj.id);
            // TODO: do this via route event handler?
            this.attr('selectedObject', obj);
        },
    });

    can.Component.extend({
        tag: 'wtf-places',
        viewModel: PlaceViewModel,
        template: can.view('app/components/places/places')
    });
});
