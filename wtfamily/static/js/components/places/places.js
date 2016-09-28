define([
    'can/component',
    'can/map',
    'can/map/define',
    'can/view/mustache',
    'app/models/place'
], function(Component, canMap, canMapDefine, Mustache, Place) {
    console.log('registering place component');
    var PlaceViewModel = canMap.extend({
        define: {
            object_list: {
                get: function() {
                    return Place.findAll({});
                },
            },
        },
    });

    Component.extend({
        tag: 'wtf-places',
        viewModel: PlaceViewModel,
        template: can.view('app/components/places/places')
    });
});
