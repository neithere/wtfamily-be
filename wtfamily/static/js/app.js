requirejs.config({
    baseUrl: '/static/js/bower_components',  // "foo" = "/static/js/lib/foo.js"
    paths: {
        lodash: 'lodash/lodash',
        jquery: 'jquery/dist/jquery',
        can: 'canjs/amd/can',
        async: 'requirejs-plugins/src/async',
        googlemaps: 'googlemaps-amd/src/googlemaps',
        bootstrap: 'bootstrap/js',
        // special paths
        app: '/static/js',      // "/app/foo" = "/static/js/foo.js"
        lib: '/static/js/lib',  // non-AMD dependencies
        basicprimitives: '/static/js/lib/primitives.min'
    },
    googlemaps: {
        params: {
            key: 'AIzaSyCJkmtBCYVPX9ImKuKdREI35RNDwPjfEQo',
            //v: '3',
            //libraries: 'geometry'
        }
    },
    shim: {
        jquery: {
            exports: ['jQuery', '$']
        },
        bootstrap: ['jquery'],
        'bootstrap/collapse': ['jquery'],
        basicprimitives: {
            deps: [
                'jquery',
                'jquery-ui/ui/widget',
                'jquery-ui/ui/widgets/button'
            ],
            exports: 'primitives'
        }
    }
});

require([
    'can/map',
    'can/route',
    'app/components/sources/sources',
    'app/components/people/people',
    'app/components/places/places',
    'app/components/places/map',
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
