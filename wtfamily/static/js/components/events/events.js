define([
    'can/component',
    'can/map',
    'can/map/define',
    'can/view/mustache',
    'app/models/event'
], function(Component, canMap, canMapDefine, Mustache, Event) {
    var EventViewModel = canMap.extend({
        define: {
            object_list: {
                get: function() {
                    return Event.findAll({});
                },
            },
        },
    });

    Component.extend({
        tag: 'wtf-events',
        viewModel: EventViewModel,
        template: can.view('app/components/events/events')
    });
});
