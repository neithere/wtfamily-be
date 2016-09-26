requirejs.config({
    baseUrl: '/static/js/lib',  // "foo" = "/static/js/lib/foo.js"
    paths: {
        app: '/static/js',       // "/app/foo" = "/static/js/foo.js"
        //'jquery-ui': '/static/js/lib/jquery-ui-1.12.1/ui',
	'jquery': '/static/js/bower_components/jquery/dist/jquery',
	'can': '/static/js/bower_components/canjs/amd/can'
    }
});

require([
    'can/map',
    'can/route',
    'can/control', 
    'can/view/mustache', 
    //'app/models/sources',
    'app/components/sources/sources',
    //'app/components/people/people',
], function(canMap, route, Control, Mustache) {
    var AppState = canMap.extend({});

    var appState = new AppState();

    // Bind the application state to the root of the application
    $('#app').html(Mustache.view('app/main', appState));

    // Set up the routes
    route(':page', { page: 'home' });
    //can.route(':page/:slug', { slug: null });
    //can.route(':page/:slug/:action', { slug: null, action: null });

    $('body').on('click', 'a[href="javascript://"]', function(ev) {
        ev.preventDefault();
    });

    // Bind the application state to the can.route
    can.route.map(appState);

    can.route.ready();
});


/*
define([
    'can/control', 
    'can/view/mustache', 
    'app/model-source'
], function(Control, Mustache, Source) {
    return Control.extend({
        init: function() {
            var objects = new Source.List({});
            var frag = Mustache.view('app/source_list', {
                //message: 'WTFamily Async Prototype!',
                object_list: objects
            });
            this.element.html(frag);
        }
    });
});
*/

/*
define([
    'can/component', 
    'can/view/mustache', 
    'app/model-source'
], function(Component, Mustache, Source) {
    return Component.extend({
        tag: 'source-index',
        scope: {

            Source: Source,

            objects: new Source.List({}),

            init: function() {
                var frag = Mustache.view('app/index', {
                    message: 'WTFamily Async Prototype',
                    object_list: this.objects
                });
                this.element.html(frag);
            }
        }
    });
});
*/
