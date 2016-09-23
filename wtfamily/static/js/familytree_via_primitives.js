requirejs(['jquery-ui.min', 'primitives.min'], function(jQueryUI, Primitives) {

    function init_family_tree (items) {
        //console.log(items);
        var options = new primitives.orgdiagram.Config();

        options.items = items;

        options.cursorItem = 0;
        options.cursorItem = 2;
        options.linesWidth = 1;
        options.linesColor = "black";
        options.hasSelectorCheckbox = primitives.common.Enabled.False;
        options.normalLevelShift = 20;
        options.dotLevelShift = 20;
        options.lineLevelShift = 20;
        options.normalItemsInterval = 10;
        options.dotItemsInterval = 10;
        options.lineItemsInterval = 10;
        options.arrowsDirection = primitives.common.GroupByType.Children;


        options.hasButtons = primitives.common.Enabled.True;
        options.onButtonClick = function (e, data) {
            var message = "User clicked '" + data.name + "' button for item '" + data.context.title + "'.";
            window.open('/person/' + data.context.id, '_blank'); //, 'location=yes,height=570,width=520,scrollbars=yes,status=yes');
        };

        options.onItemRender = onItemRender;
        options.templates = [getPersonTemplate()];

        function onItemRender(event, data) {
            var item_context = data.context;
            var fields = ['title', 'id', 'description'];
            $.each(fields, function(i, name) {
                var element = data.element.find("[name=" + name + "]");
                if (element.text() != item_context[name]) {
                    element.text(item_context[name]);
                }
            });

            // OMG, in preview mode this elem seems to be reused...
            data.element.find('[name=title]').removeClass('gender-male').removeClass('gender-female');
            if (item_context.gender == 'M') {
                data.element.find('[name=title]').addClass('gender-male');
            } else if (item_context.gender == 'F') {
                data.element.find('[name=title]').addClass('gender-female');
            }
        }

        function getPersonTemplate() {
            var result = new primitives.orgdiagram.TemplateConfig();

            result.itemTemplate =
              '<div class="bp-item bp-corner-all bp-item-frame">'+
                '<span name="title" class="bp-person-title">(TITLE)</span>'+
                '<div name="description" class="bp-person-description">(DESC)</div>' +
              '</div>';
            result.itemSize = new primitives.common.Size(150, 80);
            result.buttons = [
                new primitives.orgdiagram.ButtonConfig('detail', 'ui-icon-person', 'Detail')
            ];
            result.minimizedItemSize = new primitives.common.Size(3, 3);
            result.highlightPadding = new primitives.common.Thickness(2, 2, 2, 2);
            return result;
        }

        $("#basicdiagram").famDiagram(options);

        function focus_person(id) {
            $("#basicdiagram").famDiagram({cursorItem: id});
            $("#basicdiagram").famDiagram('update', primitives.orgdiagram.UpdateMode.Refresh)
        }

        var person_id = window.location.hash.slice(1);
        if ( person_id ) {
            focus_person(person_id);
        }
    };

    $(window).load(function () {
        // parse query string, use some params to filter data on back-end
        var params = {};
        window.location.search.replace(/[?&]+([^=&]+)=([^&]*)/gi, function(str,key,value) { params[key] = value; });
        //var url = "{{ url_for('familytree_primitives_data') }}";
        var url = "/familytree-bp/data";
        var data = {
            surname: params.surname,
            ancestors_of: params.ancestors_of,
            descendants_of: params.descendants_of,
        };
        $.getJSON(url, data).done(function(data) {
            init_family_tree(data);

            // NOTE: how to add items dynamically:
            /*
            diagram = $('#basicdiagram').data('uiFamDiagram')
            diagram.options.items.push({title:'foeu',id:'Whut', parents:['akulina']})
            diagram.update()
            */
        });
    });

});
