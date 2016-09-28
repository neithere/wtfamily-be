define([
    'can/component',
    'can/map',
    'can/map/define',
    'can/view/mustache',
    'app/models/person'
], function(Component, canMap, canMapDefine, Mustache, Person) {
    var PersonViewModel = canMap.extend({
        define: {
            object_list: {
                get: function() {
                    return Person.findAll({});
                },
            },
        },
    });

    Component.extend({
        tag: 'wtf-people',
        viewModel: PersonViewModel,
        template: can.view('app/components/people/people')
    });
});
