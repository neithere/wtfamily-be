define([
    'can/model'
], function(Model) {
    var Person = Model({
        findAll: 'GET /r/people/',
        findOne: 'GET /r/people/{id}',
        findWithRelatedPeopleIds: function(params) {
            return $.get('/r/people/', _.extend({}, params, {
                with_related_people_ids: true
            }));
        },
    }, {});

    return Person;
});
