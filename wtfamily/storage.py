import argh
from confu import Configurable


class Storage(Configurable):
    needs = {
        'path': str,
    }

    @property
    def commands(self):
        return [self.check_consistency]

    @argh.aliases('check')
    def check_consistency(self):
        # TODO:
        # for each entity
        #    for each object
        #        for each "...ref" field
        #            for each value
        #                does this ID exist?  warn if not.
        raise NotImplementedError


