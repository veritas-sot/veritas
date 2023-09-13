import logging
import uuid
import os
import yaml
from ..tools import tools


CONFIG_FILE = "../conf/journal/config.yaml"

class Journal(object):

    def __init__(self, id=None, journal_dir=None, write_at_once=False):
        self.__basedir = os.path.abspath(os.path.dirname(__file__))
        self.__metadata = {}
        self.__next_id = 0
        self.__write_at_once = write_at_once

        with open(f'{self.__basedir}/{CONFIG_FILE}') as f:
            self._journal_config = yaml.safe_load(f.read())

        try:
            filename = "%s/%s" % (
                os.path.abspath(os.path.dirname(__file__)),
                self._sot_config['journal'].get('config') 
            )
            self._journal_config = yaml.safe_load(f.read())
        except Exception as exc:
            logging.error("could not parse yaml file %s; exception: %s" % (filename, exc))

        # make a UUID based on the host address and current time
        self.__uuid = id if id else uuid.uuid1()
        jd = journal_file if journal_dir else self._journal_config.get('journal_dir','./journals')

        # if an absolut path is configured use this path
        if jd.startswith('/'):
            self.__journal_dir = f'{jd}/{self.__uuid}'
        else:
            self.__journal_dir = f'{self.__basedir}/{jd}/{self.__uuid}'

        logging.debug(f'this journal has the UIID {self.__uuid}')
        logging.debug(f'using journal_dir {self.__journal_dir}')

        # check if directory exists
        if not os.path.exists(self.__journal_dir):
            logging.debug(f'journal does not exists, creating it')
            os.makedirs(self.__journal_dir)

        # read metadata
        self._read_metadata()

    def get_uuid(self):
        return self.__uuid

    def add(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(unnamed, named)
        self.__metadata['logs'].append({'id': self.__next_id,
                                        'log': properties.get('log','no log')})
        self._write_properties(properties)
        self.__metadata['last_id'] = self.__next_id
        self.__next_id += 1
        if self.__write_at_once:
            self._write_metadata()

    def send(self, name):
        pass

    def close(self):
        self._write_metadata()

    # ---- internals ----

    def _read_metadata(self):
        if os.path.exists(f'{self.__journal_dir}/metadata.yaml'):
            with open(f'{self.__journal_dir}/metadata.yaml') as f:
                self.__metadata = yaml.safe_load(f.read())
        else:
            self.__metadata = {'last_id': 0, 'logs': []}
        self.__next_id = self.__metadata['last_id'] + 1

    def _write_metadata(self):
        with open(f'{self.__journal_dir}/metadata.yaml', "w") as f:
            f.write(yaml.dump(self.__metadata, default_flow_style=False))
    
    def _write_properties(self, properties):
        filename = f'{self.__journal_dir}/{self.__next_id}'
        with open(filename, "w") as f:
            f.write(yaml.dump(properties, default_flow_style=False))
