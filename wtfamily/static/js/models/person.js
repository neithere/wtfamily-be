define([
    'can/model'
], function(Model) {
    var Person = Model({
        findAll: 'GET /r/people/',
        findOne: 'GET /r/people/{id}',
    }, {});

    return Person;
});
