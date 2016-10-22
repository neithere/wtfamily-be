define([
    'app/models/place',
    'googlemaps!',
    'can/component',
    'can/map',
    'can/map/define',
    'can/view/mustache'
], function(Place, gmaps) {

    var MapViewModel = can.Map.extend({
        setupMap: function(map) {
            // override this
        }
    });

    var PlaceMapViewModel = MapViewModel.extend({
        setupMap: function(map) {
            Place.findAll().done(function(places) {
                var placesWithCoords = _.filter(places, 'coords');
                _.each(placesWithCoords, function(place) {
                    var position = {
                        lat: place.coords.lat,
                        lng: place.coords.lng
                    }
                    var marker = new google.maps.Marker({
                        map: map,
                        position: position,
                        title: place.name,
                        label: place.name,
                        //infowindow: ...
                    });
                });
            });
        }
    });

    var MapComponent = can.Component.extend({
        tag: 'wtf-map',
        viewModel: MapViewModel,
        template: can.view('app/components/places/map'),
        events: {
            inserted: function(el, ev) {
                var defaultPosition = {
                    lat: 52.233333,
                    lng: 21.016667
                };
                var mapElement = el.find('.map-canvas').get(0);
                var map = new gmaps.Map(mapElement, {
                    zoom: 4,
                    center: defaultPosition
                });
                //this.viewModel.attr('map', map);
                this.viewModel.setupMap(map);
            }
        },
    });

    var PlaceMapComponent = MapComponent.extend({
        tag: 'wtf-map-places',
        viewModel: PlaceMapViewModel,
    });

});
