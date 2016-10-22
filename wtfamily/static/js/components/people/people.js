define([
    'app/models/person',
    'can/component',
    'can/map',
    'can/map/define',
    'can/view/mustache',
], function(Person) {
    var PersonViewModel = can.Map.extend({
        define: {
            object_list: {
                get: function() {
                    return Person.findAll({});
                },
            },
            selectedObject: {
                value: null
            },
        },
        selectObject: function(obj, elems, event) {
            this.attr('selectedObject', obj);
        },
    });

    can.Component.extend({
        tag: 'wtf-people',
        viewModel: PersonViewModel,
        template: can.view('app/components/people/people')
    });
});
