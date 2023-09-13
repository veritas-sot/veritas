import logging
import json
from pynautobot import api
from pynautobot.models.dcim import Devices
from pynautobot.models.dcim import Interfaces
from ..tools import tools


class Interface:

    # constant values
    _interface_mandatory_properties = ['name', 'description', 'status', 'type']
    _interface_default_values = {'description': '',
                                 'status': 'active',
                                 'type': '1000base-t'}

    def __init__(self, interface_name, sot, device=None):
        logging.debug(f'initializing interface {interface_name} on {device}')
        # init variables
        self._use_defaults = False
        self._interface_defaults = {}

        # interface properties
        self._interface_name = None
        self._interface_obj = None
        self._interface_properties = {}

        # connection to nautobot
        self._nautobot = None

        self._interface_name = interface_name
        self._sot = sot
        self._device = device

    # internal method 

    def open_nautobot(self):
        if self._nautobot is None:
            self._nautobot = api(self._sot.get_nautobot_url(), token=self._sot.get_token())

    def _get_interface_from_nautobot(self, refresh=False):
        if self._interface_obj is None or refresh:
            self.open_nautobot()
            logging.debug(f'getting interface {self._interface_name} from device {self._device.name}')
            self._interface_obj = self._nautobot.dcim.interfaces.get(
                device_id=self._device.id,
                name=self._interface_name)

        return self._interface_obj

    # -----===== user commands =====----- 

    def set_interface_defaults(self, defaults):
        logging.debug(f'setting interface defaults to {defaults}')
        self._interface_defaults = defaults
        return self

    def get_properties(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(*unnamed, **named)

        if 'name' not in properties:
            properties['name'] = self._interface_name
        logging.debug(f'add interface: {self._interface_name}')

        if self._use_defaults:
            for key in self._interface_mandatory_properties:
                if key not in properties:
                    if self._use_defaults:
                        logging.error(f'mandatory property {key} is missing; using default')
                        properties[key] = self._interface_default_values.get(key)
                    else:
                        logging.error(f'mandatory property {key} is missing')
                        return None

        # convert property values to id (vlan, tags, etc.)
        success, error = self._convert_to_ids(properties)
        if not success:
            logging.error(f'could not convert properties to IDs; {error}')
            return None
        # add device name to properties if not set by user
        if 'device' not in properties:
            properties['device'] = self._device.id

        return properties

    def get(self):
        if self._interface_obj is None:
            return self._get_interface_from_nautobot()
        return self._interface_obj

    def set_tags(self, new_tags:set):
        return self.modify_tags(new_tags, False, False)

    def add_tags(self, new_tags:set):
        self.modify_tags(new_tags, True, False)

    def delete_tags(self, tags):
        self.modify_tags(tags, False, True)
      
    def modify_tags(self, tags, merge_tags=True, remove_tags=False):
        list_of_tags = set()
        self.open_nautobot()
        logging.debug(f'modify tags {list_of_tags} on interface {self._interface_name} merge: {merge_tags} remove_tags: {remove_tags}')

        # tags con be either a list or a set; convert tags to set
        if isinstance(tags, list):
            for tag in tags:
                list_of_tags.add(tag)
        elif isinstance(tags, set):
            list_of_tags = tags
        else:
            logging.error(f'list of tags must be either list or set')

        if self._device is None:
            logging.error(f'unknown device')
            return None

        interface = self._get_interface_from_nautobot(refresh=True)
        if not interface:
            logging.error(f'unknown interface {self._interface_name}')
            return None

        # merge tags: merge old and new one
        # if merge is false only the new tags are published to the interface
        if merge_tags:
            for tag in interface.tags:
                list_of_tags.add(tag.name)
        if remove_tags:
            tags = set()
            # tags that are in list_of_tags are REMOVED in this case
            for tag in interface.tags:
                if tag.name not in list_of_tags:
                    tags.add(tag.name)
            list_of_tags = tags

        logging.debug(f'current tags: {interface.tags}')
        logging.debug(f'updating tags to {list_of_tags}')

        # check if new tag is known; add id to final list
        final_list = []
        for new_tag in list_of_tags:
            tag = self._nautobot.extras.tags.get(name=new_tag)
            if tag is None:
                logging.error(f'unknown tag {new_tag}')
            else:
                final_list.append(tag.id)

        if len(final_list) > 0 or remove_tags:
            # if remove_tags is True it is possibible to set an empty list
            # in this case ALL tags are removed
            properties = {'tags': list(final_list)}
            logging.debug(f'final list of tags {properties}')
            entity = self._nautobot.dcim.interfaces.get(device_id=self._device.id, id=interface.id)
            entity.update(properties)
        else:
            logging.debug(f'empty tag list')
            return None
    
    def set_customfield(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        self.open_nautobot()
        entity = self._nautobot.dcim.interfaces.get(device=self._device.name, name=self._interface_name)
        entity.update(custom_fields=properties)

    # -----===== attributes =====-----

    def set_device(self, device):
        self._device = device
        return self

    def use_defaults(self, use_defaults):
        logging.debug(f'setting use_defaults to {use_defaults} (interface)')
        self._use_defaults = use_defaults
        return self

    # -----===== Interface Management =====-----

    def add(self, *unnamed, **named):
        self.open_nautobot()

        properties = self.get_properties(*unnamed, **named)
        return self._nautobot.dcim.interfaces.create(properties)

    def update(self, *unnamed, **named):
        self.open_nautobot()

        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        entity = self._nautobot.dcim.interfaces.get(device=self._device.name, name=self._interface_name)
        return entity.update(properties)

    def _convert_to_ids(self, newconfig, convert_device_to_uuid=True, convert_interface_to_uuid=False):
        self.open_nautobot()
        success = True
        error = ""

        if 'primary_ip4' in newconfig:
            nb_addr = self._nautobot.ipam.ip_addresses.get(address=newconfig['primary_ip4'])
            if nb_addr is None:
                success = False
                error = 'unknown IP address "%s"' % newconfig['primary_ip4']
            else:
                newconfig['primary_ip4'] = nb_addr.id

        if 'location' in newconfig:
            nb_location = self._nautobot.dcim.locations.get(slug=newconfig['location'])
            if nb_location is None:
                success = False
                error = 'unknown location "%s"' % newconfig['location']
            else:
                newconfig['location'] = nb_location.id

        if 'serial_number' in newconfig:
            # some devices have more than one serial number
            # the format is {'12345','12345'}
            newconfig['serial_number'] = newconfig['serial_number'] \
                .replace("'", "") \
                .replace("\"", "") \
                .replace("{", "") \
                .replace("}", "")

        return success, error
