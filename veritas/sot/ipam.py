from pynautobot import api
from pynautobot.models.dcim import Interfaces
from pynautobot.models.dcim import Devices
from pynautobot.models.ipam import IpAddresses
from pynautobot.models.ipam import Prefixes
from pynautobot.core.response import Record
from ..tools import tools


class Ipam(object):

    def __init__(self, sot):
        # init variables
        self._sot = sot
        self._logger = sot.get_logger()

        # open connection to nautobot
        self._nautobot = self._sot.open_nautobot()

    def add_ip(self, *unnamed, **named):
        """add IP address to ipam"""
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        try:
            return self._nautobot.ipam.ip_addresses.create(properties)
        except Exception as exc:
            self._logger.error(f'could not add ip address; got exception {exc}')
            return False
