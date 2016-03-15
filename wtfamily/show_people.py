NAME_TEMPLATE = '{first} {patronymic} {primary} ({nonpatronymic})'


def _get_name_parts(name_node):

    #print('---')
    #import pprint
    #pprint.pprint(name_node)
    #print('---')

    first = name_node.get('first', '?')
    primary_surnames = []
    patronymic = []
    nonpatronymic = []

    surname_spec = name_node.get('surname', '?')

    if isinstance(surname_spec, str):
        #primary_surnames.append(surname_spec)
        surname_spec = [
            {
                'text': surname_spec,
            }
        ]

    if isinstance(surname_spec, dict):
        surname_spec = [surname_spec]

    for surname in surname_spec:
        #print('surname:', surname)
        if isinstance(surname, str):
            surname = {
                'text': surname,
            }
        derivation = surname.get('derivation')
        is_primary = surname.get('prim') != '0'
        text = surname.get('text', '???')
        if derivation == 'Patronymic':
            patronymic.append(text)
        elif is_primary:
            primary_surnames.append(text)
        else:
            nonpatronymic.append(text)

    return first, primary_surnames, patronymic, nonpatronymic


def _format_names(name_node, template=NAME_TEMPLATE):
    if not isinstance(name_node, list):
        name_node = [name_node]
    return [_format_name(n, template=template) for n in name_node]


def _format_name(name_node, template=NAME_TEMPLATE):
    #template = '{primary} ({nonpatronymic}), {first} {patronymic}'

    first, primary_surnames, patronymic, nonpatronymic = _get_name_parts(name_node)

    ' '.join(primary_surnames)
    ' '.join(patronymic)
    ' '.join(nonpatronymic)
    return template.format(
        first = first,
        primary = ', '.join(primary_surnames),
        patronymic = ' '.join(patronymic),
        nonpatronymic = ', '.join(nonpatronymic),
    ).replace(' ()', '').strip()


def _format_dateval(dateval):
    if not dateval:
        return
    if 'val' in dateval:
        val = dateval['val']
    elif 'daterange' in dateval:
        assert 0, dateval
        val = '{}—{}'.format(
            dateval['daterange'].get('start'),
            dateval['daterange'].get('stop')
        )
    else:
        val = '?'
    vals = [
        dateval.get('quality'),
        dateval.get('type'),
        val,
    ]
    return ' '.join([x for x in vals if x])
