define([
    'app/models/source',
    'app/models/citation',
    'app/models/note',
    'lodash',
    'can/component',
    'can/map',
    'can/map/define',
    'can/view/mustache',
], function(Source, Citation, Note) {
    var SourceViewModel = can.Map.extend({
        define: {
            object_list: {
                value: function() {
                    return Source.findAll({});
                },
            },
            selectedObject: null,
            citations: {
                get: function() {
                    // Returns the list of citations for currently selected source
                    var selectedObject = this.attr('selectedObject');
                    return Citation.findWithRelated({
                        source: selectedObject.id
                    });
                },
            },
        },
        selectObject: function(obj, elems, event) {
            this.attr('selectedObject', obj);
        },
    });

    can.Component.extend({
        tag: 'wtf-sources',
        viewModel: SourceViewModel,
        template: can.view('app/components/sources/sources'),
    });
});
