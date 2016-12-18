define([
    'app/models/place',
    'can/component',
    'can/map',
    'can/map/define',
    'can/view/mustache',
], function(Place) {
    var PlaceViewModel = can.Map.extend({
        define: {
            selectedObject: {
                value: null
            },
            filterQuery: {
                value: null
            },
            object_list: {
                get: function() {
                    var query = this.attr('filterQuery');
                    /*
                    if (_.isEmpty(query)) {
                        // Require a query to avoid extremely heavy requests
                        return $.when([]);
                    }
                    */
                    return Place.findAllSorted({
                        q: query
                    });
                },
            },
            zoom: {
                value: 13
            }
        },
        selectObject: function(obj, elems, event) {
            this.attr('selectedObject', obj);
        },
    });

    can.Component.extend({
        tag: 'wtf-places',
        viewModel: PlaceViewModel,
        template: can.view('app/components/places/places')
    });
});
