import logging
import json
import os
import yaml
from pynautobot import api
from ..tools import tools


class Importer(object):

    def __init__(self, sot):
        logging.debug(f'Creating IMPORTER object;')
        self._sot = sot
        version = self._sot.get_version()
        api_version = "1.3" if version == 1 else "2.0"
        self._nautobot = api(self._sot.get_nautobot_url(), 
                             token=self._sot.get_token(), 
                             api_version=api_version)

        self._endpoints = {'sites': self._nautobot.dcim.sites,
                           'manufacturers': self._nautobot.dcim.manufacturers,
                           'platforms': self._nautobot.dcim.platforms,
                           'devices': self._nautobot.dcim.devices,
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

        if version > 1:
            # beginning with version 2 device roles are now part of extra.roles
            self._endpoints.update({'device_roles': self._nautobot.extras.roles})
        else:
            self._endpoints.update({'device_roles': self._nautobot.dcim.device_roles})

    def __getattr__(self, item):
        if item == "xxx":
            return self

    # -----===== internals =====----- 

    def open_nautobot(self):
        if self._nautobot is None:
            version = self._sot.get_version()
            api_version = "1.3" if version == 1 else "2.0"
            self._nautobot = api(self._sot.get_nautobot_url(), 
                                 token=self._sot.get_token(), 
                                 api_version=api_version)
            self._nautobot.http_session.verify = self._sot.get_ssl_verify()

    def add_entity(self, func, properties):
        try:
            item = func.create(properties)
            if item:
                logging.debug("entity added to sot")
            else:
                logging.debug("entity not added to sot")
            return item
        except Exception as exc:
            logging.error("entity not added to sot; got exception %s" % exc)
            logging.error(f'properties: {properties}')
            return None

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
            success = self.add_entity(creator, data)
            if success:
                logging.info(f'{title} successfully added to sot')
            else:
                logging.error(f'could not add {title} to sot')
        else:
            for item in data:
                success = self.add_entity(creator, item)
                if success:
                    logging.info(f'{title} successfully added to sot')
                else:
                    logging.error(f'could not add {title} to sot')
        return success

    # -----===== user commands =====----- 

    def add(self, *unnamed, **named):
        logging.debug("-- entering importer.py/add")
        self.open_nautobot()
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
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
