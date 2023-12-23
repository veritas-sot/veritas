from pynautobot import api
from ..tools import tools
from loguru import logger


class Updater(object):

    def __new__(cls, sot):
        cls._instance = None
        cls._sot = sot
        cls._nautobot = cls._sot.open_nautobot()
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
            cls._instance = super(Updater, cls).__new__(cls)
        return cls._instance

    def update_entity(self, func, properties, getter):
        """
        func: used to get the updates entity
        properties: the new properties of the entity
        """

        # check if entity is part of sot
        try:
            entity = func.get(**getter)
            if entity is None:
                logger.debug(f'entity not found in sot')
                return None
        except Exception as exc:
            logger.error(f'could not get entity; got exception {exc}')
            return None

        try:
            success = entity.update(properties)
            if success:
                logger.debug("entity updated in sot")
            else:
                logger.debug("entity not updated in sot")
            return entity
        except Exception as exc:
            logger.error("entity not updated in sot; got exception %s" % exc)
            return None

        return entity

    def update(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        endpoint_name = properties.get('endpoint')
        values = properties.get('values')
        getter = properties.get('getter')
        if endpoint_name is None or values is None or getter is None:
            logger.error('endpoint, getter, and values must be set')
            return None
        endpoint = self._endpoints.get(endpoint_name)
        return self.update_entity(endpoint, values, getter)

    def update_by_id(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        id = properties.get('id')
        del properties['id']
        d = self._nautobot.dcim.devices.update(id=id, data=properties)
