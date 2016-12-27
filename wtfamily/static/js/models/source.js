define([
    'app/models/note',
    'can/model'
], function(Note, Model) {
    var Source = Model({
        findAll: 'GET /r/sources/',
        findOne: 'GET /r/sources/{id}',
        findWithNotes: function(params) {
            return this.findAll(params).then(function(response) {
                return _.map(response, function(obj) {
                    var noteIds = _.join(obj.note_ids);
                    if (noteIds) {
                        obj.notes = Note.findAll({ids: noteIds});
                    }
                    return obj
                });
            });
        },
    }, {});

    return Source;
});
