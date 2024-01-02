import glob
import os
import yaml
import textfsm
import sys
import importlib
import logging
from loguru import logger
from importlib import resources
from scrapli import Scrapli
from scrapli_cfg import ScrapliCfg
from ..tools import tools


def get_loglevel(level):
    if level == 'debug':
        return logging.DEBUG
    elif level == 'info':
        return logging.INFO
    elif level == 'critical':
        return logging.CRITICAL
    elif level == 'error':
        return logging.ERROR
    elif level == 'none':
        return 100
    else:
        return logging.NOTSET


class Devicemanagement:

    def __init__(self, **kwargs):
        self.__ip_address = None
        self.__platform = None
        self.__manufacturer = None
        self.__username = None
        self.__password = None
        self.__port = 22
        self.__connection = None
        self.__scrapli_cfg = None

        if 'ip' in kwargs:
            self.__ip_address = kwargs['ip']
        if 'platform' in kwargs:
            self.__platform = kwargs['platform']
        if 'username' in kwargs:
            self.__username = kwargs['username']
        if 'password' in kwargs:
            self.__password = kwargs['password']
        if 'port' in kwargs:
            self.__port = kwargs['port']
        if 'manufacturer' in kwargs:
            self.__manufacturer = kwargs['manufacturer']
        if 'scrapli_loglevel' in kwargs:
            logging.getLogger('scrapli').setLevel(get_loglevel(kwargs['scrapli_loglevel']))
            logging.getLogger('scrapli').propagate = True
        else:
            logging.getLogger('scrapli').setLevel(logging.ERROR)
            logging.getLogger('scrapli').propagate = False
        # set other default values
        self._output_format = "parsed"

    def __getattr__(self, item):
        if item == "as_parsed":
            self._output_format = "parsed"
        elif item == "as_raw":
            self._output_format = "raw"
        logger.debug(f'setting putput to {self._output_format}')
        return self

    def open(self):

        # we have to map the driver to our srapli driver / platform
        #
        # napalm | scrapli
        # -------|------------
        # ios    | cisco_iosxe
        # iosxr  | cisco_iosxr
        # nxos   | cisco_nxos

        mapping = {'ios': 'cisco_iosxe',
                   'iosxr': 'cisco_iosxr',
                   'nxos': 'cisco_nxos'
                   }
        driver = mapping.get(self.__platform)
        if driver is None:
            return False

        device = {
            "host": self.__ip_address,
            "auth_username": self.__username,
            "auth_password": self.__password,
            "auth_strict_key": False,
            "platform": driver,
            "port": self.__port,
            "ssh_config_file": True
            #"ssh_config_file": "~/.ssh/ssh_config"
        }

        self.__connection = Scrapli(**device)
        logging.debug("opening connection to device (%s)" % self.__ip_address)
        try:
            self.__connection.open()
            self.__scrapli_cfg = ScrapliCfg(conn=self.__connection)
        except Exception as exc:
            logger.error(f'could not connect to {self.__ip_address}')
            return False

        return True

    def close(self):
        logger.debug("closing connection to device (%s)" % self.__ip_address)
        try:
            self.__connection.close()
        except:
            logger.error('connection was not open')

    def get_config(self, configtype):
        logger.debug("send show %s to device (%s)" % (configtype, self.__ip_address))
        if not self.__connection:
                if not self.open():
                    return None
        response = self.__connection.send_command("show %s" % configtype)
        return response.result

    def send_and_parse_command(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        directory = importlib.resources.files('veritas.devicemanagement.data.textfsm')
        logger.debug(f'directory to read textfsm is {directory}')
        result = {}
        mapped = {}
        commands = properties.get('commands')

        for cmd in commands:
            command = cmd["command"]["cmd"]
            logger.debug("sending command %s" % command)
            if not self.__connection:
                if not self.open():
                    return None
            try:
                response = self.__connection.send_command(command)
            except Exception as exc:
                logger.error("could not send command %s to device; got exception %s" % (command, exc))
                return None 

            if self._output_format == "raw":
                result[command] = response.result
                continue

            filename = cmd["command"]["template"].get(self.__platform)
            logger.debug("filename is %s" % filename)
            if filename is None:
                logger.error("no template for platform %s configured" % self.__platform)
                result[command] = {}

            if not os.path.isfile("%s/%s" % (directory, filename)):
                logger.error("template %s does not exists" % filename)
                result[command] = {}

            try:
                logger.debug("reading template")
                template = open("%s/%s" % (directory, filename))
                re_table = textfsm.TextFSM(template)
                logger.debug("parsing response")
                fsm_results = re_table.ParseText(response.result)
                collection_of_results = [dict(zip(re_table.header, pr)) for pr in fsm_results]
                result[command] = collection_of_results
            except Exception as exc:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                logger.error("parser error in line %s; got: %s (%s, %s, %s)" % (exc_tb.tb_lineno,
                                                                                 exc,
                                                                                 exc_type,
                                                                                 exc_obj,
                                                                                 exc_tb))
                result[command] = {}

            # check if we have a mapping
            # the mapping is used to rename parameters from the result eg.
            # INTF to interface in show ip int brief
            if 'mapping' in cmd["command"]:
                logger.debug(f'mapping is enabled {cmd["command"]["mapping"]}')
                if command not in mapped:
                    mapped[command] = []
                for res in result[command]:
                    m = {}
                    for key, value in res.items():
                        is_mapped = False
                        for map in cmd["command"]['mapping']:
                            if key == map["src"]:
                                m[map["dst"]] = value
                                is_mapped = True
                        if not is_mapped:
                            m[key] = value
                    mapped[command].append(m)
                result = mapped

        return result

    def get_facts(self):
        directory = importlib.resources.files('veritas.devicemanagement.data.facts')
        logger.debug(f'reading facts config from {directory}')

        files = []
        facts = {}
        values = {}
        # read all facts from config
        for filename in glob.glob(os.path.join(directory, "*.yaml")):
            with open(filename) as f:
                logger.debug("opening file %s to read facts config" % filename)
                try:
                    config = yaml.safe_load(f.read())
                    if config is None:
                        logger.error("could not parse file %s" % filename)
                        continue
                except Exception as exc:
                    logger.error("could not read file %s; got exception %s" % (filename, exc))
                    continue

                active = config.get('active')
                name = config.get('name')
                if not active:
                    logger.debug("config context %s in %s is not active" % (name, filename))
                    continue

                file_vendor = config.get("vendor")
                if file_vendor is None or file_vendor != self.__manufacturer:
                    logger.debug("skipping file %s (%s)" % (filename, file_vendor))
                    continue

                files.append(os.path.basename(filename))
                values = self.send_and_parse_command(commands=config['facts'])
                if values is None:
                    return None

        facts["manufacturer"] = self.__manufacturer
        if "show version" in values:
            facts["os_version"] = values["show version"][0].get("VERSION",None)
            if facts["os_version"] is None:
                # nxos uses OS instead of version
                facts["os_version"] = values["show version"][0].get('OS', 'unknown')
            facts["software_image"] = values["show version"][0].get("SOFTWARE_IMAGE", None)
            if facts["software_image"] is None:
                # nxos uses BOOT_IMAGE instead of SOFTWARE_IMAGE
                facts["software_image"] = values["show version"][0].get("BOOT_IMAGE",'unknown')
            facts["serial_number"] = values["show version"][0]["SERIAL"]
            if 'HARDWARE' in values["show version"][0]:
                facts["model"] = values["show version"][0]["HARDWARE"][0]
            else:
                # nxos uses PLATFORM instead of HARDWARE
                model = values["show version"][0].get('PLATFORM',None)
                if model is None:
                    facts["model"] = "default_type"
                else:
                    facts["model"] = "nexus-%s" % model
            facts["hostname"] = values["show version"][0]["HOSTNAME"]

        if "show hosts" in values and len(values["show hosts"]) > 0:
            facts["fqdn"] = "%s.%s" % (facts.get("hostname"), values["show hosts"][0]["DEFAULT_DOMAIN"])
        else:
            facts["fqdn"] = facts.get("hostname")

        # hostnames and fqdn are always lower case
        facts['fqdn'] = facts['fqdn'].lower()
        facts['hostname'] = facts['hostname'].lower()

        logger.debug("processed %s to get facts of device" % files)
        #print(json.dumps(facts, indent=4))

        return facts

    def execute(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        platform = properties.get('platform', self.__platform)
        manufacturer = properties.get('manufacturer', self.__manufacturer)
        # guess template
        cmd = properties.get('cmd').replace(' ', '_')
        tmpl = f"{manufacturer}_{platform}_{cmd}.textfsm"
        cmds = {'command': {
                'cmd': properties.get('cmd'), 
                'template': {
                    platform: properties.get('template', tmpl)
                }
              }
             }
        if 'mapping' in properties:
            cmds['command'].update({'mapping': properties.get('mapping')})
        return self.send_and_parse_command(commands=[cmds])

    def write_config(self):
        if not self.__connection:
                if not self.open():
                    return None
        logger.debug(f'writing config on device {self.__ip_address}')
        return self.__scrapli_cfg.save_config()

    def send_configs_from_file(self, configfile, hostname="", dry_run=False):
        if not self.__connection:
                if not self.open():
                    return False
        logger.debug(f'sending config {configfile} to device {hostname}/{self.__ip_address}')
        if dry_run:
            print(f'sending config {configfile} to device {hostname}/{self.__ip_address}')
            return True
        return self.__connection.send_configs_from_file(configfile)

    def send_commands(self, commands):
        if not self.__connection:
            if not self.open():
                return None

        return self.__connection.send_commands(commands)

    def send_configs(self, commands):
        if not self.__connection:
            if not self.open():
                return None

        return self.__connection.send_configs(commands)
