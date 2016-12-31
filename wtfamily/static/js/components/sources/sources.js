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
        selectedObject: null,
        filterQuery: null,
        define: {
            object_list: {
                get: function() {
                    var query = this.attr('filterQuery');
                    return Source.findWithNotes({
                        q: query
                    });
                },
            },
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
        tag: 'wtf-sources',
        viewModel: SourceViewModel,
        template: can.view('app/components/sources/sources'),
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
                var selectedObject = viewModel.attr('selectedObject');
                var viewModelObjId = _.get(selectedObject, 'id');
                var routeObjId = can.route.attr('objId');
                if (viewModelObjId !== routeObjId) {
                    can.route.attr('objId', viewModelObjId);
                }
            }
        }
    });
});
