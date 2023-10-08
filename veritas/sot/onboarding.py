import logging
import json
import re
import sys
from netaddr import IPNetwork
from pynautobot import api
from pynautobot.models.dcim import Devices
from pynautobot.models.dcim import Interfaces as PyInterfaces
from pynautobot.models.ipam import IpAddresses
from . import ipam
from .. import devicemanagement as dm
from ..tools import tools


class Onboarding:
    """Class to onboard devices to nautobot

    Attributes
    ----------

    Methods
    -------

    Examples to use
    ---------------

    sot.device(device_fqdn) \
                .interface(interface_properties) \
                .make_primary(True) \
                .add(device_properties)

    sot.device(device_fqdn) \
                .interface(list_of_interface_properties) \
                .primary_interface(name_of_interface) \
                .make_primary(True) \
                .add(device_properties)
    """

    def __init__(self, sot):
        logging.debug(f'initializing ONBOARDING object')

        self._sot = sot
        self._make_interface_primary = False
        self._primary_interface = None
        self._is_primary = False
        self._interfaces = []
        self._add_prefix = True
        self._assign_ip = True
        self._use_device_if_already_exists = True
        self._use_interface_if_already_exists = True
        self._use_ip_if_already_exists = True

        # open connection to nautobot
        self._nautobot = self._sot.open_nautobot()

    # ---------- fluent attributes ----------

    def make_primary(self, make_primary):
        logging.debug(f'making interface the primary interface')
        self._make_interface_primary = True
        return self

    def interface(self, *unnamed, **named):
        """add interface to nautobot"""
        logging.debug(f'adding interface to list of interfaces')
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        if isinstance (properties, list):
            for property in properties:
                self._interfaces.append(property)
        else:
            self._interfaces.append(properties)
        return self

    def primary_interface(self, primary_interface):
        """set primary interface"""
        logging.debug(f'setting primary interface to {primary_interface}')
        self._primary_interface = primary_interface
        return self

    def use_device_if_exists(self, use_device):
        """use device if device already exists in nautobot"""
        logging.debug(f'setting _use_device_if_already_exists to {use_device}')
        self._use_device_if_already_exists = use_device
        return self

    def use_interface_if_exists(self, use_interface):
        """use interface if interface already exists in nautobot"""
        logging.debug(f'setting _use_interface_if_already_exists to {use_interface}')
        self._use_interface_if_already_exists = use_interface
        return self

    def use_ip_if_exists(self, use_ip):
        """use IP if IP already exists in nautobot"""
        logging.debug(f'setting _use_ip_if_already_exists to {use_ip}')
        self._use_ip_if_already_exists = use_ip
        return self

    def add_prefix(self, add_prefix):
        """set add_prefix"""
        logging.debug(f'setting _add_prefix to {add_prefix}')
        self._add_prefix = add_prefix
        return self

    def is_primary(self, is_primary):
        """set is_primary"""
        logging.debug(f'setting _is_primary to {is_primary}')
        self._is_primary = is_primary
        return self

    def assign_ip(self, assign_ip):
        """set assign_ip"""
        logging.debug(f'setting _assign_ip to {assign_ip}')
        self._assign_ip = assign_ip
        return self

    # ---------- commands ----------

    def add_device(self, *unnamed, **named):
        """add device to nautobot"""
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        
        """ we have to modify some attributes like device_type and role"""
        if 'device_type' in properties:
            properties['device_type'] = {'model': properties['device_type']}
        if 'role' in properties:
            properties['role'] = {'name': properties['role']}
        if 'manufacturer' in properties:
            properties['manufacturer'] = {'name': properties['manufacturer']}

        logging.debug(f'properties: {properties}')
        device = self._add_device_to_nautobot(properties)
        # add  interface(s) to device
        if device and len(self._interfaces) > 0:
            response = self._add_interfaces_to_nautobot(device)
            for interface in self._interfaces:
                ipv4 = interface.get('ipv4')
                if ipv4:
                    nb_interface = self._nautobot.dcim.interfaces.get(
                        device_id=device.id,
                        name=interface.get('name'))
                    ip_address = self._add_ipv4_to_nautbot(device, ipv4)
                    assign = self._assign_ipaddress_to_interface(device, nb_interface, ip_address)

        if device and self._add_prefix:
            prefix = self._add_prefix_to_nautobot()

        return device

    # ---------- methods ----------

    def _add_device_to_nautobot(self, device_properties):
        """add device to nautobot"""
        
        try:
            device_name = device_properties.get('name')
            logging.error(f'adding device {device_name} to SOT')
            device = self._nautobot.dcim.devices.create(device_properties)
            if device is None:
                logging.error(f'could not add device {device_name} to SOT')
                return None
            return device
        except Exception as exc:
            if 'A device with this name already exists' in str(exc):
                logging.debug(f'a device with this name already exists')
                if self._use_device_if_already_exists:
                    return self._nautobot.dcim.devices.get(name=device_name)
            else:
                logging.error(exc)
        return None 

    def _add_interfaces_to_nautobot(self, device):
        """add interfaces to nautobot"""
        logging.debug(f'adding {len(self._interfaces)} interfaces to device {device}')

        # check if device id is in interface properties
        interfaces = list(self._interfaces)
        for interface in interfaces:
            if not 'device' in interface:
                interface['device'] = device.id
            # if 'ipv4' in interface:
            #     del interface['ipv4']
        logging.debug(f'adding list of interfaces {interfaces}')
        return self._nautobot.dcim.interfaces.create(interfaces)

    def _add_prefix_to_nautobot(self, ipv4):
        """add prefix to nautobot"""
        if not '/' in ipv4:
            logging.error(f'cannot add prefix to nautobot; no mask found in primary_ipv4')
        ip = IPNetwork(ipv4)

        logging.debug(f'network={ip.network} prefixlen={ip.prefixlen}')
        properties = {'prefix': f'{ip.network}/{ip.prefixlen}',
                      'status': {'name': 'Active'}}
        try:
            return self._nautobot.ipam.prefixes.create(properties)
        except Exception as exc:
            print(exc)

    def _add_ipv4_to_nautbot(self, device, ipv4):
        """add IPv4 to nautobot"""
        logging.debug(f'adding IPv4 {ipv4} to nautobot')

        properties = {'address': ipv4,
                      'status': {'name': 'Active'},
                      'namespace': 'Global'}
        try:
            return self._nautobot.ipam.ip_addresses.create(properties)
        except Exception as exc:
            if 'duplicate key value violates unique constraint' in str(exc):
                logging.debug(f'this IP address already exists')
                if self._use_ip_if_already_exists:
                    return self._nautobot.ipam.ip_addresses.get(
                        address=ipv4)
            else:
                logging.error(exc)
        return None 

    def _assign_ipaddress_to_interface(self, device, interface, ip_address):
        """assign IPv4 address to interface of device"""
        logging.debug(f'assigning IP {ip_address} to {device}/{interface.display}')

        try:
            return self._nautobot.ipam.ip_address_to_interface.create(
                {"interface": interface.id,
                "ip_address": ip_address.id}
            )
        except Exception as exc:
            if 'The fields interface, ip_address must make a unique set.' in str(exc):
                logging.debug(f'this IP address is already assigned')
                return True
            else:
                logging.error(exc)
        return False 