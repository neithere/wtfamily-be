define([
    'app/models/person',
    'basicprimitives',
    'can/component',
    'can/map',
    'can/map/define',
    'can/view/mustache'
], function(Person, promisedPrimitives) {

    var FamilyTreeViewModel = can.Map.extend({
        define: {
            initialPeopleIds: {
                'set': function(newValue) {
                    return newValue
                }
            }
        },
        diagramElementId: 'familyTreeDiagram',
        diagramWidth: '100%',
        diagramHeight: '90%',
    });

    can.Component.extend({
        tag: 'wtf-familytree',
        viewModel: FamilyTreeViewModel,
        template: can.view('app/components/familytree/familytree'),
        events: {
            inserted: function(el, ev) {
                var initialPeopleIds = this.viewModel.attr('initialPeopleIds');
                var diagramElementId = this.viewModel.attr('diagramElementId');
                var diagramElement = el.find('#' + diagramElementId);

                $.when(
                    promisedPrimitives
                ).then(
                    fetchInitialData.bind(this, initialPeopleIds)
                ).then(
                    prepareOptions.bind(this, diagramElement)
                ).then(
                    initDiagram.bind(this, diagramElement)
                ).then(function(diagram) {
                    this._diagram = diagram;
                });
            },
        },
    });

    function fetchRelativesFor(personId) {
        return Person.findWithRelatedPeopleIds({
            relatives_of: personId,
            with_related_people_ids: true
        });
    }

    function loadRelativesFor(diagramElement, personId) {
        return fetchRelativesFor(personId).then(function(relatives) {
            var diagram = diagramElement.data('uiFamDiagram');

            _.each(relatives, function(relative) {
                diagram.options.items.push(relative);
            }.bind(this));

            diagram.update();

        }.bind(this)).promise();
    }

    function onPersonSelected(el, ev, data) {
        var target = $(ev.originalEvent.target);
        var personData = data.context;
        var personId = personData.id;
        var cardElem = $('.bp-item[data-personId="' + personId + '"]');

        cardElem.addClass('loading');
        loadRelativesFor(el, personId).then(function() {
            cardElem.removeClass('loading');
        }.bind(this));
    }

    function onItemRender(event, data) {
        var tmpl = 
          '<div class="bp-item bp-corner-all bp-item-frame" data-personId="{{id}}">'+
            '<span class="bp-person-title {{#eq gender "M"}}gender-male{{/eq}} {{#eq gender "F"}}gender-female{{/eq}}">{{first_and_last_names}}</span>'+
            '<div class="bp-person-description">' +
            '  <span>{{birth}} — {{death}}</span>' +
            '</div>'
          '</div>';
        var html = can.view.mustache(tmpl)(data.context);
        data.element.html(html);
    }

    function prepareOptions(diagramElement, initialData) {
        var options = new primitives.orgdiagram.Config();
        var itemTemplate = getPersonTemplate();

        options.items = initialData;

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

        options.onCursorChanged = onPersonSelected.bind(this, diagramElement);

        options.onItemRender = onItemRender;
        options.templates = [itemTemplate];

        return options;
    }

    function getPersonTemplate() {
        var result = new primitives.orgdiagram.TemplateConfig();
        var itemWidth = 150;
        var itemHeight = 70;
        var minimizedItemSize = 6;

        result.itemTemplate = '<div></div>';
        result.itemSize = new primitives.common.Size(itemWidth, itemHeight);
        result.minimizedItemSize = new primitives.common.Size(minimizedItemSize, minimizedItemSize);
        result.highlightPadding = new primitives.common.Thickness(2, 2, 2, 2);
        return result;
    }

    function initDiagram(diagramElement, options) {
        var el = diagramElement;
        var diagram;

        // instantiate the diagram and attach to the element
        el.famDiagram(options);

        diagram = el.data('uiFamDiagram');

        return diagram;
    }

    function fetchInitialData(initialPeopleIds) {
        return Person.findWithRelatedPeopleIds({
            ids: initialPeopleIds
        });
    }
});
