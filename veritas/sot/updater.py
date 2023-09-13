import logging
from pynautobot import api
from . import central


class Updater(object):

    def __new__(cls, sot):
        cls._instance = None
        cls._sot = sot
        cls._nautobot = api(cls._sot.get_nautobot_url(), token=cls._sot.get_token(), api_version=1.3)
        cls._endpoints = {'sites': cls._nautobot.dcim.sites,
                          'manufacturers': cls._nautobot.dcim.manufacturers,
                          'platforms': cls._nautobot.dcim.platforms,
                          'devices': cls._nautobot.dcim.devices,
                          'device_roles': cls._nautobot.dcim.device_roles,
                          'prefixes': cls._nautobot.ipam.prefixes,
                          'location_types': cls._nautobot.dcim.location_types,
                          'locations': cls._nautobot.dcim.locations,
                          'interface_templates': cls._nautobot.dcim.interface_templates,
                          'tags': cls._nautobot.extras.tags,
                          'custom_fields': cls._nautobot.extras.custom_fields,
                          'custom_field_choices': cls._nautobot.extras.custom_field_choices,
                          'webhooks': cls._nautobot.extras.webhooks,
                          'device_types': cls._nautobot.dcim.device_types,
                          'console_port_templates': cls._nautobot.dcim.console_port_templates,
                          'power_port_templates': cls._nautobot.dcim.power_port_templates,
                          'device_bay_templates': cls._nautobot.dcim.device_bay_templates, }
                
        # singleton
        if cls._instance is None:
            logging.debug(f'Creating UPDATER object')
            cls._instance = super(Updater, cls).__new__(cls)
        return cls._instance

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

    def open_nautobot(self):
        if self._nautobot is None:
            self._nautobot = api(self._sot.get_nautobot_url(), token=self._sot.get_token())

    def update(self, *unnamed, **named):
        logging.debug("-- entering sot/updater.py/update")
        properties = self.__convert_arguments_to_properties(*unnamed, **named)
        endpoint_name = properties.get('endpoint')
        values = properties.get('values')
        getter = properties.get('getter')
        if endpoint_name is None or values is None or getter is None:
            logging.error('endpoint, getter, and values must be set')
            return None
        endpoint = self._endpoints.get(endpoint_name)
        return self._sot.central.update_entity(endpoint, values, getter)

    def update_by_id(self, *unnamed, **named):
        logging.debug("-- entering sot/updater.py/update_by_id")
        properties = self.__convert_arguments_to_properties(*unnamed, **named)
        self.open_nautobot()
        id = properties.get('id')
        del properties['id']
        d = self._nautobot.dcim.devices.update(id=id, data=properties)
        print(d)

