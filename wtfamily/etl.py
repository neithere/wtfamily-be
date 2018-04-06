#    WTFamily is a genealogical software.
#
#    Copyright © 2014—2018  Andrey Mikhaylenko
#
#    This file is part of WTFamily.
#
#    WTFamily is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    WTFamily is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with WTFamily.  If not, see <http://gnu.org/licenses/>.
from confu import Configurable

from storage import Storage
from gramps_xml_to_yaml import extract, transform, load


class WTFamilyETL(Configurable):
    needs = {
        'gramps_xml_path': str,
        'storage': Storage,
    }

    def import_gramps_xml(self, path=None, dry_run=False):
        xml_root = extract(path or self.gramps_xml_path)
        items = transform(xml_root)
        for entity_name, pk, data in items:
            self.storage.add(entity_name, pk, data, upsert=True, commit=False)
        if not dry_run:
            self.storage.commit()

    @property
    def commands(self):
        return [self.import_gramps_xml]
