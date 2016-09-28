define([
    'can/model'
], function(Model) {
    var Note = Model({
        findAll: 'GET /r/notes/',
        findOne: 'GET /r/notes/{id}',
    }, {});

    return Note;
});
