define([
    'app/models/place',
    'googlemaps!',
    'can/component',
    'can/map',
    'can/map/define',
    'can/view/mustache'
], function(Place, gmaps) {

    var MapViewModel = can.Map.extend({
        defaultPosition: null,
        defaultZoom: 4,
        map: null,
        setupMap: function(map) {
            // override this
        }
    });

    var PlaceMapViewModel = MapViewModel.extend({
        map: null,
        place: null,
        setupMap: function(map) {
            this.attr('map', map);
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
                        placeObj: place,
                        //infowindow: ...
                    });
                    marker.addListener('click', function() {
                        this.attr('place', marker.placeObj);
                    }.bind(this));
                }.bind(this));
            }.bind(this));
        }
    });

    var MapComponent = can.Component.extend({
        tag: 'wtf-map',
        viewModel: MapViewModel,
        template: can.view('app/components/places/map'),
        events: {
            inserted: function(el, ev) {
                var defaultPosition = this.viewModel.defaultPosition;
                var defaultZoom = this.viewModel.defaultZoom;
                var mapElement = el.find('.map-canvas').get(0);
                var map = new gmaps.Map(mapElement, {
                    zoom: defaultZoom,
                    center: defaultPosition
                });
                this.viewModel.setupMap(map);
            }
        }
    });

    var PlaceMapComponent = MapComponent.extend({
        tag: 'wtf-map-places',
        viewModel: PlaceMapViewModel,
        events: _.extend({}, MapComponent.events, {
            // FIXME code is duplicated; apparently Component is not intended
            // to be inherited and doesn't allow easy code reuse — rather
            // aggregation of functionality
            inserted: function(el, ev) {
                var defaultPosition = this.viewModel.defaultPosition || {
                    lat: 52.233333,
                    lng: 21.016667
                };
                var defaultZoom = this.viewModel.defaultZoom;
                var mapElement = el.find('.map-canvas').get(0);
                var map = new gmaps.Map(mapElement, {
                    zoom: defaultZoom,
                    center: defaultPosition
                });
                this.viewModel.setupMap(map);
            },
            '{scope} place': function() {
                var map = this.viewModel.attr('map');
                var place = this.viewModel.attr('place');
                if (_.isNull(map)) {
                    return;
                }
                if (_.isEmpty(place) || _.isEmpty(place.coords)) {
                    return;
                }
                this.viewModel.map.panTo(place.coords);
            }
        })
    });

});
