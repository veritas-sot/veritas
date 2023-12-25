import os
import yaml
import json
import sys
import textfsm
from loguru import logger
from veritas.sot import sot as sot
from veritas.inventory import veritasInventory
from veritas.tools import tools
from nornir import InitNornir
from nornir.core.plugins.inventory import InventoryPluginRegister
from nornir_napalm.plugins.tasks import napalm_get, napalm_ping
from nornir_utils.plugins.tasks.files import write_file
from nornir_utils.plugins.functions import print_result
from nornir_scrapli.tasks import (
    get_prompt,
    send_command,
    send_commands,
    send_configs
)


class Job(object):

    def __init__(self, sot, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(unnamed, named)
        InventoryPluginRegister.register("veritas-inventory", veritasInventory.VeritasInventory)

        self._sot = sot
        self._nornir = None
        self._nautobot = None
        self.__on = None
        self.__host_groups = []
        self.__groups = {}
        self.__result = properties.get('result','raw')
        self.__username = properties.get('username')
        self.__password = properties.get('password')
        self.__port = properties.get('port',22)
        self.__data = properties.get('data',{})
        self.__user_primary = properties.get('use_primary', True)
        self.__logging = properties.get('logging',{"enabled": False})

    def init_nornir(self, *unnamed, **named):
        # returns the nornir object so that the user can 
        # run its own tasks
        properties = tools.convert_arguments_to_properties(unnamed, named)
        if not self._nornir:
            self._init_nornir(properties)
        return self._nornir 

    def __getattr__(self, item):
        if item.startswith('get_'):
            return self._getter(item)
        elif 'is_alive' == item:
            return self._direct(item)
        else:
            raise AttributeError (f'unknown attribute')

    def open_nautobot(self):
        if self._nautobot is None:
            self._nautobot = api(self._sot.get_nautobot_url(), token=self._sot.get_token())

    def on(self, *unnamed, **named):
        self.__on = tools.convert_arguments_to_properties(unnamed, named)
        return self

    def set(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(unnamed, named)

        self.__username = properties.get('username')
        self.__password = properties.get('password')
        self.__result = properties.get('result', self.__result)
        self.__parse_result = properties.get('parse', False)
        self.__port = properties.get('port', self.__port)
        self.__cfg_plain_text = properties.get('plaintext', True)
        self.__user_primary = properties.get('use_primary', self.__user_primary)
        self.__logging = properties.get('logger', self.__logging)
        return self

    def add_data(self, *unnamed, **named):
        # we expect a list and add this list to our inventory data later
        properties = tools.convert_arguments_to_properties(unnamed, named)
        self.__data = [properties] if isinstance(properties, str) else properties
        return self

    def add_group(self, *unnamed, **named):
        # we expect a dict
        properties = tools.convert_arguments_to_properties(unnamed, named)
        self.__groups = properties
        return self

    def add_to_group(self, *unnamed, **named):
        # we expect a list
        properties = tools.convert_arguments_to_properties(unnamed, named)
        self.__host_groups = [properties] if isinstance(properties, str) else properties
        return self

    def ping(self,  *unnamed, **named):
        properties = tools.convert_arguments_to_properties(unnamed, named)
        destination = properties.get('destination')
        count = properties.get('count',3)

        logger.info(f'ping {destination} {count}')
        self._init_nornir()
        result = self._nornir.run(name="ping", 
                                  task=napalm_ping, 
                                  dest=destination,
                                  count=count)
        return self._return(result)

    def get_config(self, *unnamed, **named):

        # get properties
        properties = tools.convert_arguments_to_properties(unnamed, named)
        config = properties if len(properties) > 0 else "running"
        logger.debug(f'getting {config} config')

        # init nornir
        self._init_nornir()
        result = self._nornir.run(
            name="get_config", task=napalm_get, getters=['config'], retrieve=config
        )
        return self._return(result)

    def send_configs(self, commands):

        logger.debug(f'send config {commands}')
        self._init_nornir()
        result = self._nornir.run(
            name="send_configs", task=send_configs, configs=commands
        )
        return self._return(result)

    def send_command(self, command):

        logger.debug(f'send command {command}')
        self._init_nornir()
        result = self._nornir.run(
            name=command, task=send_command, command=command
        )
        return self._return(result)

    def send_commands(self, commands):

        logger.debug(f'send commands {commands}')
        self._init_nornir()
        result = self._nornir.run(
            name="Send commands", task=send_commands, commands=commands
        )
        return self._return(result)

    # -------- internal methods --------

    def _init_nornir(self, *unnamed, **named):

        if self._nornir is not None:
            return 

        properties = tools.convert_arguments_to_properties(unnamed, named)
        _data = properties.get('data', self.__data)
        _host_groups = properties.get('data', self.__host_groups)
        _groups = properties.get('groups', self.__groups)
        _logger = properties.get('logger', self.__logging)
        _worker = properties.get('num_workers', 100)

        self._nornir = InitNornir(
            runner={
                "plugin": "threaded",
                "options": {
                    "num_workers": _worker,
                },
            },
            inventory={
                'plugin': 'veritas-inventory',
                "options": {
                    'url': self._sot.get_nautobot_url(),
                    'token': self._sot.get_token(),
                    'query': self.__on,
                    'use_primary_ip': self.__user_primary,
                    'username': self.__username,
                    'password': self.__password,
                    'connection_options': {'default': {'username': self.__username,
                                                       'password': self.__password,
                                                       'port': self.__port}
                                        },
                    'data': _data,
                    'host_groups': _host_groups,
                    'groups': _groups
                },
            },
            logging=self.__logging,
        )

    def _getter(self, getter):

        logger.info(f'getter {getter}')
        self._init_nornir()
        result = self._nornir.run(name=getter, task=napalm_get, getters=getter)
        return self._return(result)

    def _direct(self, service):

        logger.info(f'is alive')
        self._init_nornir()
        if 'is_alive' == service:
            task = self._is_alive

        result = self._nornir.run(name=service, task=task)
        return self._return(result)

    def _is_alive(self, task):
        napalm = task.host.get_connection("napalm", task.nornir.config)
        alive = napalm.is_alive()

    def _normalize_result(self, results):
        response = {}

        for hostname in results:
            if hostname not in response:
                response[hostname] = {}
            result = results[hostname].result
            command = results[hostname].name.replace(' ','_')
            response[hostname][command] = result
        
        return response

    def _return(self, result):

        if self.__parse_result:
            return self._parse_result(result)
        elif 'normalize' == self.__result:
            return self._normalize_result(result)
        else:
            return result

    def _parse_result(self, results):
        BASEDIR = os.path.abspath(os.path.dirname(__file__))
        template_directory = os.path.join(BASEDIR, '../textfsm')
        response = {}
        for hostname in results:
            if hostname not in response:
                response[hostname] = {}
            host = self._nornir.inventory.hosts[hostname]
            platform = host.get('platform','ios')
            manufacturer = host.get('manufacturer','cisco')
            result = results[hostname].result
            command = results[hostname].name.replace(' ','_')
            filename = f'{manufacturer}_{platform}_{command}.textfsm'
            logger.info(f'result of {hostname} manufacturer: {manufacturer} platform {platform}')
            logger.info(f'using template {filename}')

            if command == "get_config":
                # it is either a startup or a running config
                if len(result.get('config').get('running')) > 0:
                    if self.__cfg_plain_text and len(results) == 2:
                        # one host / user wants just the config
                        return result.get('config').get('running')
                    response[hostname][command] = result.get('config').get('running')
                elif len(result.get('config').get('startup')) > 0:
                    if self.__cfg_plain_text and len(results) == 2:
                        # one host / user wants just the config
                        return result.get('config').get('startup')
                    response[hostname][command] = result.get('config').get('startup')
                else:
                    response[hostname][command] = result
                continue

            # check if template exists
            if not os.path.isfile("%s/%s" % (template_directory, filename)):
                logger.error("template %s does not exists" % filename)
                return results
            # now parse result using this template
            try:
                template = open("%s/%s" % (template_directory, filename))
                re_table = textfsm.TextFSM(template)
                fsm_results = re_table.ParseText(result)
                collection_of_results = [dict(zip(re_table.header, pr)) for pr in fsm_results]
                response[hostname][command] = collection_of_results
            except Exception as exc:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("parser error in line %s; got: %s (%s, %s, %s)" % (exc_tb.tb_lineno,
                                                                                 exc,
                                                                                 exc_type,
                                                                                 exc_obj,
                                                                                 exc_tb))
                response[hostname][command] = {}

        return response
