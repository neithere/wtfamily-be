define([
    'can/model'
], function(Model) {
    var Person = Model({
        findAll: 'GET /r/people/',
        findOne: 'GET /r/people/{id}',
        findAllSorted: function(params) {
            return this.findAll(params).then(function(items) {
                return _.sortBy(items, 'name');
            });
        },
        findWithRelatedPeopleIds: function(params) {
            return $.get('/r/people/', _.extend({}, params, {
                with_related_people_ids: true
            }));
        },
        findByNameGroup: function(groupName) {
            return $.get('/r/people/', {by_namegroup: groupName});
        },
    }, {});

    return Person;
});
