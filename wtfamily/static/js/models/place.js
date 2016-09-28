define([
    'can/model'
], function(Model) {
    var Place = Model({
        findAll: 'GET /r/places/',
        findOne: 'GET /r/places/{id}',
    }, {});

    return Place;
});
