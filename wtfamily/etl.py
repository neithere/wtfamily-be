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
