requirejs.config({
    baseUrl: '/static/js/bower_components',  // "foo" = "/static/js/lib/foo.js"
    paths: {
        lodash: 'lodash/lodash',
        jquery: 'jquery/dist/jquery',
        can: 'canjs/amd/can',
        // special paths
        app: '/static/js',      // "/app/foo" = "/static/js/foo.js"
        lib: '/static/js/lib',  // non-AMD dependencies
    }
});

require([
    'can/map',
    'can/route',
    'app/components/sources/sources',
    'app/components/people/people',
    'app/components/places/places',
    'app/components/events/events',
    'app/components/familytree/familytree',
], function() {
    var AppState = can.Map.extend({});

    var appState = new AppState();

    // Bind the application state to the root of the application
    $('#app').html(can.view('app/main', appState));

    // Set up the routes
    can.route(':page', { page: 'home' });

    $('body').on('click', 'a[href="javascript://"]', function(ev) {
        ev.preventDefault();
    });

    // Bind the application state to the can.route
    can.route.map(appState);

    can.route.ready();
});
