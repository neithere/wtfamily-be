define([
    'can/model'
], function(Model) {
    var Place = Model({
        findAll: 'GET /r/places/',
        findOne: 'GET /r/places/{id}',
        findAllSorted: function(params) {
            return this.findAll(params).then(function(items) {
                return _.sortBy(items, 'name');
            });
        },
    }, {});

    return Place;
});
