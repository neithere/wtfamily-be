define([
    'app/models/person',
    'app/models/namegroup',
    'can/component',
    'can/map',
    'can/map/define',
    'can/view/mustache',
    'bootstrap/collapse'
], function(Person, NameGroup) {
    var PersonViewModel = can.Map.extend({
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
                    if (_.isEmpty(query)) {
                        // Require a query to avoid extremely heavy requests
                        return $.when([]);
                    }
                    return Person.findAllSorted({
                        q: query
                    });
                },
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
