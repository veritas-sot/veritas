from loguru import logger
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

        # open connection to nautobot
        self._nautobot = self._sot.open_nautobot()

    def add_ip(self, *unnamed, **named):
        """add IP address to ipam"""
        properties = tools.convert_arguments_to_properties(*unnamed, **named)

        try:
            return self._nautobot.ipam.ip_addresses.create(properties)
        except Exception as exc:
            logger.bind(extra=properties.get("address","unset")).error(f'could not add ip address; got exception {exc}')
            return False

    def get_ip(self, *unnamed, **named):
        """get IP address from ipam"""
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        address = properties.get('address')
        # if there is a / use address only
        address = address.split('/')[0]
        namepace = properties.get('namespace','Global')
        logger.debug(f'getting IP {address} namespace {namespace}')
        return self._nautobot.ipam.ip_addresses.get(address=address,
                                                    namespace=namespace)

