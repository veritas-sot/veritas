import logging
import json
import re
import sys
from . import interfaces
from . import ipam
from pynautobot import api
from pynautobot.models.dcim import Devices
from pynautobot.models.dcim import Interfaces as PyInterfaces
from pynautobot.models.ipam import IpAddresses
from .. import devicemanagement as dm
from ..tools import tools


class Device:
 
    def __init__(self, sot, device):
        logging.debug(f'initializing DEVICE object {device}')

        # init variables
        self._sot = sot
        self._device = device
    
        # open connection to nautobot
        self._nautobot = self._sot.open_nautobot()

    def set_customfield(self, *unnamed, **named):
        """set customfield of device / interface"""
        logging.debug(f'set customfield of device {self._device}')
        properties = tools.convert_arguments_to_properties(*unnamed, **named)

        device = self._nautobot.dcim.devices.get(name=self._device)
        if device:
            update = device.update(properties)
            return update
        else:
            logging.error(f'device {self._device} not found')
            return False        
