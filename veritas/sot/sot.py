import os
import json
import yaml
import importlib.machinery
from importlib import resources
from dotenv import load_dotenv, dotenv_values
from pynautobot import api
from loguru import logger
from . import ipam
from . import getter
from . import selection
from . import onboarding
from . import device as dvc
from . import importer
from . import auth
from . import configparser
from . import updater
from . import rest
from . import repository
from . import job


class Sot:

    def __init__(self, **properties):
        # initialize variables
        self.__onboarding = None
        self.__ipam = None
        self.__getter = None
        self.__selection = None
        self.__importer = None
        self.__auth = None
        self._nautobot = None
        self.__configparser = None
        self.__updater = None
        self.__job = None
        self._sot_config = {}

        logger.debug(f'reading SOT config')
        package = f'{__name__.split(".")[0]}.sot.data.sot'
        with resources.open_text(package, 'config.yaml') as f:
            self._sot_config = yaml.safe_load(f.read())

        self._sot_config['nautobot_url'] = properties.get('url')
        self._sot_config['nautobot_token'] = properties.get('token')
        self._sot_config['ssl_verify'] = properties.get('ssl_verify')
        self._sot_config['git'] = properties.get('git')

    def __getattr__(self, item):
        if item == "onboarding":
            if self.__onboarding is None:
                self.__onboarding = onboarding.Onboarding(self)
            return self.__onboarding
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
        if item == "updater":
            if self.__updater is None:
                self.__updater = updater.Updater(self)
            return self.__updater
        if item == "job":
            if self.__job is None:
                self.__job = job.Job(self)
            return self.__job

    def registry(self, module, path=None):
        if not path:
            path = f'{self.BASEDIR}/{module}.py'
        return importlib.machinery.SourceFileLoader(module,path).load_module()

    def device(self, device):
        return dvc.Device(self, device)

    def get_token(self):
        return self._sot_config['nautobot_token']

    def get_ssl_verify(self):
        return self._sot_config['ssl_verify']

    def get_nautobot_url(self):
        return self._sot_config['nautobot_url']

    def get_git(self):
        return self._sot_config['git']

    def get_config(self):
        return self._sot_config

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
    
    def open_nautobot(self):
        if self._nautobot is None:
            api_version = self._sot_config.get('version','2.0')
            ssl_verify = self._sot_config['ssl_verify']
            logger.debug(f'nautobot api object created; version={api_version} ssl_verify={ssl_verify}')
            self._nautobot = api(self._sot_config['nautobot_url'], 
                                 token=self._sot_config['nautobot_token'], 
                                 api_version=api_version)
            self._nautobot.http_session.verify = ssl_verify

        return self._nautobot
