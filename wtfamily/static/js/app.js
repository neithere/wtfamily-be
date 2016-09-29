requirejs.config({
    baseUrl: '/static/js/bower_components',  // "foo" = "/static/js/lib/foo.js"
    paths: {
        app: '/static/js',      // "/app/foo" = "/static/js/foo.js"
        lodash: 'lodash/lodash',
        jquery: 'jquery/dist/jquery',
        can: 'canjs/amd/can'
    }
});

require([
    'can/map',
    'can/route',
    'can/control', 
    'can/view/mustache', 
    'app/components/sources/sources',
    'app/components/people/people',
    'app/components/places/places',
    'app/components/events/events',
], function(canMap, route, Control, Mustache) {
    var AppState = canMap.extend({});

    var appState = new AppState();

    // Bind the application state to the root of the application
    $('#app').html(Mustache.view('app/main', appState));

    // Set up the routes
    route(':page', { page: 'home' });

    $('body').on('click', 'a[href="javascript://"]', function(ev) {
        ev.preventDefault();
    });

    // Bind the application state to the can.route
    can.route.map(appState);

    can.route.ready();
});