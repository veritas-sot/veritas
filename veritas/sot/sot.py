import logging
import os
import json
import yaml
from dotenv import load_dotenv, dotenv_values
from . import device
from . import ipam
from . import getter
from . import selection
from . import device
from . import importer
from . import auth
from . import analyzer
from . import configparser
from . import updater
from . import rest
from . import repository
from . import job


class Sot:

    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    DEFAULT_CONFIGFILE = "../conf/sot/sot/config.yaml"

    def __init__(self, **properties):
        # initialize variables
        self.__devices = {}
        self.__ipam = None
        self.__getter = None
        self.__selection = None
        self.__importer = None
        self.__auth = None
        self.__analyzer = None
        self.__configparser = None
        self.__updater = None
        self.__job = None
        self._sot_config = {}

        filename = properties['sot_config'] if 'sot_config' in properties else self.DEFAULT_CONFIGFILE
        logging.debug("reading SOT config %s/%s" % (self.BASEDIR, filename))
        with open(f'{self.BASEDIR}/{filename}') as f:
            self._sot_config = yaml.safe_load(f.read())

        self._sot_config['nautobot_url'] = properties.get('url')
        self._sot_config['nautobot_token'] = properties.get('token')
        self._sot_config['git'] = properties.get('git')

    def __getattr__(self, item):
        if item == "ipam":
            if self.__ipam is None:
                self.__ipam = ipam.Ipam(self)
            return self.__ipam
        if item == "get":
            if self.__getter is None:
                self.__getter = getter.Getter(self)
            return self.__getter
        if item == "importer":
            if self.__importer is None:
                self.__importer = importer.Importer(self)
            return self.__importer
        if item == "auth":
            if self.__auth is None:
                self.__auth = auth.Auth(self)
            return self.__auth
        if item == "analyzer":
            if self.__analyzer is None:
                self.__analyzer = analyzer.Analyzer(self)
            return self.__analyzer
        if item == "updater":
            if self.__updater is None:
                self.__updater = updater.Updater(self)
            return self.__updater
        if item == "job":
            if self.__job is None:
                self.__job = job.Job(self)
            return self.__job

    def get_token(self):
        return self._sot_config['nautobot_token']

    def get_nautobot_url(self):
        return self._sot_config['nautobot_url']

    def get_git(self):
        return self._sot_config['git']

    def get_config(self):
        return self._sot_config

    def device(self, name):
        if name not in self.__devices:
            self.__devices[name] = device.Device(self, name)
        return self.__devices[name]

    def select(self, *unnamed, **named):
        return selection.Selection(self, *unnamed, **named)

    def configparser(self, *unnamed, **named):
        return configparser.Configparser(self, *unnamed, **named)

    def rest(self, *unnamed, **named):
        return rest.Rest(self, *unnamed, **named)

    def repository(self, **named):
        return repository.Repository(**named)

    def auth(self, **parameter):
        if self.__auth is None:
            self.__auth = auth.Auth(self, **parameter)
        return self.__auth