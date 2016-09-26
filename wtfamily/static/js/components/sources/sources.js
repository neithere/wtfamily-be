define([
    'can/component', 
    'can/map', 
    'can/map/define', 
    'can/view/mustache', 
    'app/models/source'
], function(Component, canMap, canMapDefine, Mustache, Source) {
    var SourceViewModel = canMap.extend({
        define: {
            sources: {
                get: function() {
                    return Source.findAll({});
                },
            },
        },
    });

    Component.extend({
        tag: 'wtf-sources',
        viewModel: SourceViewModel,
        template: can.view('app/components/sources/sources')
    });
});
