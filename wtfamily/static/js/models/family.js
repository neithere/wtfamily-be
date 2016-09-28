define([
    'can/model'
], function(Model) {
    var Family = Model({
        findAll: 'GET /r/families/',
        findOne: 'GET /r/families/{id}',
    }, {});

    return Family;
});
