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
                    });
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
            this.attr('selectedObject', obj);
        },
        selectObjectById: function(objId) {
            if (_.isEmpty(objId)) {
                return
            }
            this.attr('object_list').done(function(results) {
                var obj = _.find(results, {id: objId});
                this.attr('selectedObject', obj);
            }.bind(this));
        }
    });

    can.Component.extend({
        tag: 'wtf-places',
        viewModel: PlaceViewModel,
        template: can.view('app/components/places/places'),
        init: function() {
            // select an item according to the active route
            var objId = can.route.attr('objId');
            this.viewModel.selectObjectById(objId);
        },
        events: {
            '{can.route} change': function(data) {
                // route changed → select respective object
                this.viewModel.selectObjectById(data.attr('objId'));
            },
            '{viewModel}.selectedObject change': function(viewModel) {
                // object selected → update current route
                // (e.g. if the selection was changed by a click on the map)
                var viewModelObjId = viewModel.attr('selectedObject').id;
                var routeObjId = can.route.attr('objId');
                if (viewModelObjId !== routeObjId) {
                    can.route.attr('objId', viewModelObjId);
                }
            }
        }
    });
});
