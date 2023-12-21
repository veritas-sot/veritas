import json
import re
import sys
from . import ipam
from pynautobot import api
from pynautobot.models.dcim import Devices
from pynautobot.models.dcim import Interfaces as PyInterfaces
from pynautobot.models.ipam import IpAddresses
from .. import devicemanagement as dm
from ..tools import tools


class Device:
 
    def __init__(self, sot, device):
        # init variables
        self._sot = sot
        self._logger = sot.get_logger()
        self._device = device
        self._interface = None

        # open connection to nautobot
        self._nautobot = self._sot.open_nautobot()

    def interface(self, interface_name):
        self._interface = interface_name
        return self

    def update(self, *unnamed, **named):
        """update device or interface"""
     
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        if self._interface:
            return self.update_interface(properties)

        self._logger.debug(f'update device {self._device}')
        device = self._nautobot.dcim.devices.get(name=self._device)
        if device:
            update = device.update(properties)
            self._logger.debug(f'update device result={update}')
            return update
        else:
            self._logger.error(f'device {self._device} not found')
            return False        

    def update_interface(self, properties):
        """update interface on device"""
        interface = self._nautobot.dcim.interfaces.get(
                    device=[self._device],
                    name=self._interface)

        if not interface:
            self._logger.error(f'unknown interface {self._interface} on {self._device}')
            return False

        try:
            return interface.update(properties)
        except Exception as exc:
            self._logger.error(f'could not update interface; got exception {exc}')
            return False

    def set_tags(self, new_tags):
        if self._interface:
            return self.add_interface_tags(new_tags, set_tag=True)
        else:
            return self.add_tags(new_tags, set_tag=True)

    def add_tags(self, new_tags, set_tag=False):
        """add tags on device"""
        if self._interface:
            return self.add_interface_tags(new_tags, set_tag=False)

        final_list = []

        if not set_tag:
            # if the device already exists there may also be tags
            device = self._nautobot.dcim.devices.get(name=self._device)
            if device is None:
                self._logger.error(f'unknown device {self._device_name}')
                return False

            for tag in device.tags:
                if tag.name not in new_tags:
                    new_tags.append(tag.name)

            self._logger.debug(f'current tags: {device.tags}')
            self._logger.debug(f'updating tags to {new_tags}')

        # check if new tag is known; add id to final list
        for new_tag in new_tags:
            tag = self._nautobot.extras.tags.get(name=new_tag)
            if tag is None:
                self._logger.error(f'unknown tag {new_tag}')
            else:
                final_list.append(tag.id)

        if len(final_list) > 0:
            properties = {'tags': final_list}
            self._logger.debug(f'final list of tags {properties}')
            return self.update(properties)

    def delete_tags(self, tags_to_delete):
        if self._interface:
            return self.delete_interface_tags(tags_to_delete)
        
        self._logger.debug(f'deleting tags {tags_to_delete} on {self._device}')

        # the device must exist; get tags
        device = self._nautobot.dcim.devices.get(name=self._device)
        if device is None:
            self._logger.error(f'unknown device {self._device}')
            return None

        device_tags = []
        current_tags = []
        for tag in device.tags:
            current_tags.append(tag.name)
            if tag.name not in tags_to_delete:
                device_tags.append(tag)

        self._logger.debug(f'current tags: {current_tags}')
        self._logger.debug(f'new tags {device_tags}')

        properties = {'tags': device_tags}
        return self.update(properties)

    def add_interface_tags(self, new_tags, set_tag=False):
        """add tags on interface"""
        final_list = []

        interface = self._nautobot.dcim.interfaces.get(
                    device=[self._device],
                    name=self._interface)

        if not interface:
            self._logger.error(f'unknown interface {self._interface} on {self._device}')
            return False

        if not set_tag:
            for tag in interface.tags:
                if tag.name not in new_tags:
                    new_tags.append(tag.name)

            self._logger.debug(f'current tags: {interface.tags}')
            self._logger.debug(f'updating tags to {new_tags}')

        # check if new tag is known; add id to final list
        for new_tag in new_tags:
            tag = self._nautobot.extras.tags.get(name=new_tag)
            if tag is None:
                self._logger.error(f'unknown tag {new_tag}')
            else:
                final_list.append(tag.name)

        if len(final_list) > 0:
            properties = {'tags': final_list}
            self._logger.debug(f'final list of tags {properties}')
            try:
                return interface.update(properties)
            except Exception as exc:
                self._logger.error(f'could not update interface; got exception {exc}')
                return False

    def delete_interface_tags(self, tags_to_delete):
        self._logger.debug(f'deleting tags {tags_to_delete} on {self._device}/{self._interface}')

        interface = self._nautobot.dcim.interfaces.get(
                    device=[self._device],
                    name=self._interface)

        if not interface:
            self._logger.error(f'unknown interface {self._interface} on {self._device}')
            return False

        interface_tags = []
        current_tags = []
        for tag in interface.tags:
            current_tags.append(tag.name)
            if tag.name not in tags_to_delete:
                interface_tags.append(tag)

        self._logger.debug(f'current tags: {current_tags}')
        self._logger.debug(f'new tags {interface_tags}')

        properties = {'tags': interface_tags}
        try:
            return interface.update(properties)
        except Exception as exc:
            self._logger.error(f'could not delete tags on interface; got exception {exc}')
            return False

    def set_customfield(self, properties):
        """set custom field on device or interface"""
        if self._interface:
            return self.set_interface_customfield(properties)

        device = self._nautobot.dcim.devices.get(name=self._device)
        if device is None:
            self._logger.error(f'unknown device {self._device_name}')
            return False
    
        return device.update(properties)

    def set_interface_customfield(self, properties):
        interface = self._nautobot.dcim.interfaces.get(
                    device=[self._device],
                    name=self._interface)

        if not interface:
            self._logger.error(f'unknown interface {self._interface} on {self._device}')
            return False
        try:
            return interface.update(properties)
        except Exception as exc:
            self._logger.error(f'could not update interface; got exception {exc}')
            return False
