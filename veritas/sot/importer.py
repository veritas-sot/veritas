import logging
import json
import os
import yaml
from pynautobot import api


class Importer(object):

    def __init__(self, sot):
        logging.debug(f'Creating IMPORTER object;')
        self._sot = sot
        self._nautobot = api(self._sot.get_nautobot_url(), token=self._sot.get_token(), api_version=1.3)

        self._endpoints = {'sites': self._nautobot.dcim.sites,
                           'manufacturers': self._nautobot.dcim.manufacturers,
                           'platforms': self._nautobot.dcim.platforms,
                           'devices': self._nautobot.dcim.devices,
                           'device_roles': self._nautobot.dcim.device_roles,
                           'prefixes': self._nautobot.ipam.prefixes,
                           'location_types': self._nautobot.dcim.location_types,
                           'locations': self._nautobot.dcim.locations,
                           'interface_templates': self._nautobot.dcim.interface_templates,
                           'tags': self._nautobot.extras.tags,
                           'custom_fields': self._nautobot.extras.custom_fields,
                           'custom_field_choices': self._nautobot.extras.custom_field_choices,
                           'custom_links': self._nautobot.extras.custom_links,
                           'webhooks': self._nautobot.extras.webhooks,
                           'device_types': self._nautobot.dcim.device_types,
                           'console_port_templates': self._nautobot.dcim.console_port_templates,
                           'power_port_templates': self._nautobot.dcim.power_port_templates,
                           'device_bay_templates': self._nautobot.dcim.device_bay_templates,}

    def __getattr__(self, item):
        if item == "xxx":
            return self

    # -----===== internals =====----- 

    def open_nautobot(self):
        if self._nautobot is None:
            self._nautobot = api(self._sot.get_nautobot_url(), token=self._sot.get_token())

    def __convert_arguments_to_properties(self, *unnamed, **named):
        """ converts unnamed (dict) and named arguments to a single property dict """
        properties = {}
        if len(unnamed) > 0:
            for param in unnamed:
                if isinstance(param, dict):
                    for key,value in param.items():
                        properties[key] = value
                elif isinstance(param, str):
                    # it is just a text like log('something to log')
                    return param
                elif isinstance(param, tuple):
                    for tup in param:
                        if isinstance(tup, dict):
                            for key,value in tup.items():
                                properties[key] = value
                        if isinstance(tup, str):
                            return tup
                elif isinstance(param, list):
                    return param
                else:
                    logging.error(f'cannot use paramater {param} / {type(param)} as value')
        for key,value in named.items():
                properties[key] = value
        
        return properties

    def open_file(self, filename):
        logging.debug(f'opening file {filename}')
        with open(filename) as f:
            try:
                content = yaml.safe_load(f.read())
            except Exception as exc:
                logging.error("could not read file %s; got exception %s" % (filename, exc))
                return None
        return content

    def import_data(self, data, title, creator, bulk=False):
        logging.debug("-- entering importer.py/import_data")
        self.open_nautobot()
        success = False

        if bulk:
            success = self._sot.central.add_entity(creator, data)
            if success:
                logging.info(f'{title} successfully added to sot')
            else:
                logging.error(f'could not add {title} to sot')
        else:
            for item in data:
                success = self._sot.central.add_entity(creator, item)
                if success:
                    logging.info(f'{title} successfully added to sot')
                else:
                    logging.error(f'could not add {title} to sot')
        return success

    # -----===== user commands =====----- 

    def add(self, *unnamed, **named):
        logging.debug("-- entering importer.py/add")
        self.open_nautobot()
        properties = self.__convert_arguments_to_properties(*unnamed, **named)
        endpoint = properties.get('endpoint')
        if not endpoint:
            logging.error(f'please specify endpoint')
            return False
        bulk=properties.get('bulk', False)

        if 'file' in properties:
            content = self.open_file(properties['file'])
            return self.import_data(content['interface_templates'], endpoint, self._endpoints[endpoint])
        elif 'properties' in properties:
            return self.import_data(properties['properties'], endpoint, self._endpoints[endpoint], bulk=bulk)
