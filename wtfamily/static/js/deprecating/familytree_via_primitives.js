requirejs.config({
    baseUrl: '/static/js/bower_components',
    paths: {
        lodash: 'lodash/lodash',
        jquery: 'jquery/dist/jquery',
        'jquery-ui': 'jquery-ui/ui',
        primitives_non_amd: '/static/js/lib/primitives.min'
    }
});

define('jquery', ['jquery.min'], function() {
    return jQuery;
});

define('primitives', ['jquery', 'jquery-ui/widget', 'jquery-ui/widgets/button'], function(jQuery, jquery_ui) {
    var deferred = $.Deferred();
    var req2 = require(['primitives_non_amd'], function(foo) {
        deferred.resolve(primitives);
    });
    return deferred.promise();
});

define('FamilyTree', ['jquery', 'lodash', 'primitives'], function($, _, promisedPrimitives) {

    function init(config) {
        var url = config.url;
        var params = config.params;

        $.getJSON(url, params).done(function(data) {
            this.init_family_tree(data);
        }.bind(this));
    };

    function init_family_tree(items) {
        $.when(promisedPrimitives).then(function(primitives) {
            _init_family_tree(items, primitives);
        });

    };

    function fetchRelativesFor(personId) {
        var url = "/familytree-bp/data";
        var params = {
            relatives_of: personId
        };
        return $.getJSON(url, params);
    }

    function loadRelativesFor(personId) {
        return fetchRelativesFor(personId).then(function(relatives) {
            var diagram = $('#basicdiagram').data('uiFamDiagram');

            _.each(relatives, function(relative) {
                diagram.options.items.push(relative);
            }.bind(this));

            diagram.update();

        }.bind(this)).promise();
    };

    function _init_family_tree(items, primitives) {
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

        options.onCursorChanged = function(e, data) {
            var target = $(e.originalEvent.target);
            var cardElem = target.closest('.bp-item');
            var personData = data.context;
            var personId = personData.id;

            cardElem.addClass('loading');
            loadRelativesFor(personId).then(function() {
                cardElem.removeClass('loading');
            }.bind(this));
        }


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

    return {
        init: init,
        init_family_tree: init_family_tree
    };
});

require(['FamilyTree'], function(FamilyTree) {

    console.debug('preparing to initialize the family tree...');

    // parse query string, use some params to filter data on back-end
    var params = {};
    window.location.search.replace(/[?&]+([^=&]+)=([^&]*)/gi, function(str,key,value) { params[key] = value; });
    //var url = "{{ url_for('familytree_primitives_data') }}";
    var url = "/familytree-bp/data";
    var urlParams = {
        surname: params.surname,
        ancestors_of: params.ancestors_of,
        descendants_of: params.descendants_of,
        relatives_of: params.relatives_of,
        single_person: params.single_person,
    };
    FamilyTree.init({
        url: url,
        params: urlParams
    });
});
