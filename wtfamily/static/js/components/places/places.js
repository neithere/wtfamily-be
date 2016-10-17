define([
    'app/models/place',
    'can/component',
    'can/map',
    'can/map/define',
    'can/view/mustache'
], function(Place) {
    var PlaceViewModel = can.Map.extend({
        define: {
            object_list: {
                get: function() {
                    return Place.findAll({});
                },
            },
        },
    });

    can.Component.extend({
        tag: 'wtf-places',
        viewModel: PlaceViewModel,
        template: can.view('app/components/places/places')
    });
});
