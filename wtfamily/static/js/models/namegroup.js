define([
    'can/model',
], function(Model) {
    var NameGroup = Model({
        findAll: 'GET /r/person_name_groups',
    }, {});

    return NameGroup;
});
