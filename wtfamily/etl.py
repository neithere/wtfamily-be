from confu import Configurable

from storage import Storage
from gramps_xml_to_yaml import extract, transform, load


class WTFamilyETL(Configurable):
    needs = {
        'gramps_xml_path': str,
        'storage': Storage,
    }

    def import_gramps_xml(self):
        xml_root = extract(self.gramps_xml_path)
        items = transform(xml_root)
        loaded = load(items, self.storage.path)   # FIXME this should use Storage API;
                                                  # all YAML stuff should be there
        # trigger the process
        for x in loaded:
            pass

    @property
    def commands(self):
        return [self.import_gramps_xml]
