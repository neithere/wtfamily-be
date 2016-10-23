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
            object_groups: {
                get: function() {
                    // add index to each group because the don't have IDs
                    // but the template needs something to identify them
                    return NameGroup.findAll({}).then(function(items) {
                        return _.map(items, function(item, i) {
                            item.index = i;
                            return item;
                        });
                    });
                },
            },
            object_list: {
                value: null,
            },
            selectedObject: {
                value: null
            },
        },
        selectGroup: function(obj, elems, event) {
            var objectList;
            var isExpandingGroup = elems.attr('aria-expanded') === 'false';

            if (isExpandingGroup) {
                // TODO: make it faster — supply person IDs with group data
                // and make a simple /r/people/?ids=x,y,z request
                objectList = Person.findByNameGroup(obj.name);
                this.attr('object_list', objectList);
            }
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
