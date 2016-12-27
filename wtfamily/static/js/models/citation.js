define([
    'can/model',
    'app/models/event',
    'app/models/note'
], function(Model, Event, Note) {
    var Citation = Model({
        findOne: 'GET /r/citations/{id}',
        findAll: 'GET /r/citations/',
        findWithRelated: function(params) {
            return this.findAll(params).then(function(response) {
                var sortedCitations = _.sortBy(response, 'date');
                return _.map(sortedCitations, function(citation) {
                     var noteIds = _.join(citation.note_ids);
                     if (noteIds) {
                         citation.notes = Note.findAll({ids: noteIds});
                     }
                     citation.events = Event.findWithRelated({proven_by: citation.id});
                     return citation
                });
            });
        },
    }, {});

    return Citation;
});
