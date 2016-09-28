define([
    'can/model'
], function(Model) {
    var Source = Model({
        findAll: 'GET /r/sources/',
        findOne: 'GET /r/sources/{id}',
    }, {});

    return Source;
});
