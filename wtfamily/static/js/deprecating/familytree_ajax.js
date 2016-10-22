window.drawFamilyTree = function() {
    var ftree = new FamilyTreeJS.FamilyTree();
    ftree.config.node.width = 120;
    ftree.config.node.height = 30;
    ftree.config.node.spacingVertical = 45;
    //ftree.config.compressable = false;

    // mapping of identifiers (from data) to Person objects (in FamilyTree)
    var person_by_id = {};

    function add_person(data, key){
        console.log(key);
        if (person_by_id.hasOwnProperty(key)) {
            return person_by_id[key];
        }
        var data_item = data[key];

        // add parents to the family tree
        for (var i in data_item.parents) {
            parent_id = data_item.parents[i];
            if (!person_by_id.hasOwnProperty(parent_id)) {
                person_by_id[parent_id] = add_person(data, parent_id);
            }
        }

        // add person to the family tree
        person = ftree.AddPerson(data_item.name, {blurb: data_item.blurb});
        console.log('  created', person);
        person_by_id[key] = person;

        // add mutual references (order in which people are registered in the
        // tree is important, so we have two loops instead of one)
        for (var i in data_item.parents) {
            parent_id = data_item.parents[i];
            var parent_obj = person_by_id[parent_id];
            person.parents.push(parent_obj);
            parent_obj.children.push(person);
        }
        return person;
    }

    $.getJSON('/familytree.json', function(data) {
        for (var key in data) {
            add_person(data, key);
        }
        ftree.Render(document.getElementById('familytree'));
    });
}

