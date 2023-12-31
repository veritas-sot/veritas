import json
import re
import sys
from loguru import logger
from netaddr import IPNetwork
from pynautobot import api
from pynautobot.models.dcim import Devices
from pynautobot.models.dcim import Interfaces as PyInterfaces
from pynautobot.models.ipam import IpAddresses
from . import ipam
from .. import devicemanagement as dm
from ..tools import tools


class Onboarding:
    """Class to onboard devices including interfaces and tags to nautobot

    Attributes
    ----------

    Methods
    -------

    Examples to use
    ---------------

    sot.device(device_fqdn) \
                .interface(interface_properties) \
                .primary_interface(name_of_interface) \
                .add(device_properties)

    sot.device(device_fqdn) \
                .interface(list_of_interface_properties) \
                .primary_interface(name_of_interface) \
                .add(device_properties)
    
    sot.onboarding \
                .add_prefix(False) \
                .assign_ip(True) \
                .add_interfaces(device=device, interfaces=interfaces)
    """

    def __init__(self, sot):
        self._sot = sot
        self._make_interface_primary = False
        self._primary_interface = ""
        self._is_primary = False
        self._interfaces = []
        self._vlans = []
        self._add_prefix = True
        self._assign_ip = True
        self._bulk = True
        self._use_device_if_already_exists = True
        self._use_interface_if_already_exists = True
        self._use_ip_if_already_exists = True

        # open connection to nautobot
        self._nautobot = self._sot.open_nautobot()

    # ---------- fluent attributes ----------

    def interfaces(self, *unnamed, **named):
        """add interface to nautobot"""
        logger.debug(f'adding interface to list of interfaces')
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        # empty list!!!
        self._interfaces = []
        if isinstance (properties, list):
            for property in properties:
                self._interfaces.append(property)
        else:
            self._interfaces.append(properties)
        return self

    def vlans(self, *unnamed, **named):
        """add vlans to nautobot"""
        logger.debug(f'adding vlan to list of VLANS')
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        # empty list!!!
        self._vlans = []
        if isinstance (properties, list):
            for property in properties:
                self._vlans.append(property)
        else:
            self._vlans.append(properties)
        return self

    def primary_interface(self, primary_interface):
        """set primary interface"""
        logger.debug(f'setting primary interface to {primary_interface}')
        self._primary_interface = primary_interface
        return self

    def use_device_if_exists(self, use_device):
        """use device if device already exists in nautobot"""
        logger.debug(f'setting _use_device_if_already_exists to {use_device}')
        self._use_device_if_already_exists = use_device
        return self

    def use_interface_if_exists(self, use_interface):
        """use interface if interface already exists in nautobot"""
        logger.debug(f'setting _use_interface_if_already_exists to {use_interface}')
        self._use_interface_if_already_exists = use_interface
        return self

    def use_ip_if_exists(self, use_ip):
        """use IP if IP already exists in nautobot"""
        logger.debug(f'setting _use_ip_if_already_exists to {use_ip}')
        self._use_ip_if_already_exists = use_ip
        return self

    def add_prefix(self, add_prefix):
        """set add_prefix"""
        logger.debug(f'setting _add_prefix to {add_prefix}')
        self._add_prefix = add_prefix
        return self

    def assign_ip(self, assign_ip):
        """set assign_ip"""
        logger.debug(f'setting _assign_ip to {assign_ip}')
        self._assign_ip = assign_ip
        return self

    def bulk(self, bulk):
        """set bulk"""
        logger.debug(f'setting _bulk to {bulk}')
        self._bulk = bulk
        return self

    # ---------- user commands ----------

    def add_device(self, *unnamed, **named):
        """add device to nautobot"""
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        logger.debug(f'properties: {properties}')

        # add device to nautobot
        device = self._add_device_to_nautobot(properties)

        # first of all VLANs are added to the SOT
        if device and len(self._vlans) > 0:
            self._add_vlans_to_nautobot()

        # now add the interfaces of this device
        # either the interfaces are part of our properties or were
        # configured using .interface(list_of_ifaces)
        interfaces = properties.get('interfaces', self._interfaces)
        self.add_interfaces(device=device, interfaces=interfaces)

        return device

    def add_interfaces(self, *unnamed, **named):
        """add interfaces to nautobot"""
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        v_response = p_response = prefix = assign = True

        # get device object and interface properties
        device = properties.get('device')
        interfaces = properties.get('interfaces')
        logger.debug(f'adding interfaces to {device}')

        # now add the virtual and physical interfaces
        virtual_interfaces = []
        physical_interfaces = []
        for interface in interfaces:
            if interface and 'port-channel' in interface['name'].lower():
                virtual_interfaces.append(interface)
            else:
                physical_interfaces.append(interface)
        logger.debug(f'summary: adding {len(virtual_interfaces)} virtual and {len(physical_interfaces)} physical interfaces')

        if device and len(interfaces) > 0:
            # add interfces to nautobot
            v_response = self._add_interfaces_to_nautobot(device, virtual_interfaces)
            p_response = self._add_interfaces_to_nautobot(device, physical_interfaces)
            # the interfaces were added; now add the IP addresses of ALL interfaces
            for interface in interfaces:
                ip_addresses = interface.get('ip_addresses',[])
                # an interface can have more than one IP, so it is a list of IPs!!!
                if len(ip_addresses) > 0:
                    logger.debug(f'found {len(ip_addresses)} IP(s) on device {device} {interface.get("name")}')
                    # add description to each IP address
                    for addr in ip_addresses:
                        addr['description'] = f'{device} {interface.get("name")}'
                    if self._add_prefix:
                        prefix = self._add_prefix_to_nautobot(ip_addresses)

                    added_addresses = self._add_ipaddress_to_nautbot(device, ip_addresses)
                    if len(added_addresses) > 0:
                        # get interface object from nautobot
                        nb_interface = self._nautobot.dcim.interfaces.get(
                                    device_id=device.id,
                                    name=interface.get('name'))
                        for ip_address in added_addresses:
                            if self._assign_ip:
                                if nb_interface:
                                    assign = self._assign_ipaddress_to_interface(device, nb_interface, ip_address)
                                    logger.debug(f'assigned IPv4 {ip_address} on device {device} / nb_interface')
                                else:
                                    logger.error(f'could not get interface {device.name}/{interface.get("name")}')

        # what value should we return?
        return v_response and p_response and prefix and assign

    def update_interfaces(self, *unnamed, **named):
        """update interfaces(s) of device"""
        properties = tools.convert_arguments_to_properties(*unnamed, **named)

        # get device object and interface properties
        device = properties.get('device')
        interfaces = properties.get('interfaces')
        logger.debug(f'updating interfaces of {device}')

        if not device or len(interfaces) == 0:
            logger.debug(f'either no device found or len(interfaces) == 0')
            return False

        for interface in interfaces:
            # get interface object from nautobot
            nb_interface = self._nautobot.dcim.interfaces.get(
                            device_id=device.id,
                            name=interface.get('name'))
            nb_interface.update(interface)
            # remove ALL assigments
            self._remove_all_assignments(device, nb_interface)

            ip_addresses = interface.get('ip_addresses',[])
            # an interface can have more than one IP, so it is a list of IPs!!!
            # we are now (re)adding all assigments
            if len(ip_addresses) > 0:
                logger.debug(f'found {len(ip_addresses)} IP(s) on device {device} {interface.get("name")}')
                # add description to each IP address
                for addr in ip_addresses:
                    addr['description'] = f'{device} {interface.get("name")}'
                if self._add_prefix:
                    prefix = self._add_prefix_to_nautobot(ip_addresses)
                
                added_addresses = self._add_ipaddress_to_nautbot(device, ip_addresses)
                if len(added_addresses) > 0:
                    for ip_address in added_addresses:
                        if self._assign_ip:
                            if nb_interface:
                                assign = self._assign_ipaddress_to_interface(device, nb_interface, ip_address)
                                logger.debug(f'assigned IPv4 {ip_address.display} on device {device} / nb_interface')
                            else:
                                logger.error(f'could not get interface {device.name}/{interface.get("name")}')
        return True

    def set_primary_address(self, address, device):
        """set primary address on device"""

        if isinstance(address, str):
            ip_address = self._nautobot.ipam.ip_addresses.get(address=address)
        else:
            ip_address = address
        if not isinstance(ip_address, IpAddresses):
            logger.error(f'no valid ip address found')
            return False
        
        try:
            return device.update({'primary_ip4': ip_address.id})
        except Exception as exc:
            if 'is not assigned to this device' in str(exc):
                logger.error(f'the address {ip_address.display} is not assigned to {device.name}')
                return False

    # ---------- internal methods ----------

    def _add_device_to_nautobot(self, device_properties):
        """add device to nautobot"""
        
        try:
            device_name = device_properties.get('name')
            logger.info(f'adding device {device_name} to SOT')
            device = self._nautobot.dcim.devices.create(device_properties)
            if device is None:
                logger.error(f'could not add device {device_name} to SOT')
                return None
            return device
        except Exception as exc:
            if 'A device with this name already exists' in str(exc):
                logger.debug(f'a device with this name already exists')
                if self._use_device_if_already_exists:
                    return self._nautobot.dcim.devices.get(name=device_name)
            else:
                logger.error(exc)
        return None 

    def _add_vlans_to_nautobot(self):
        logger.debug(f'adding VLANs to nautobot')
        # check if vlan exists
        new_vlans = []
        for vlan in self._vlans:
            vid = vlan.get('vid')
            location = vlan.get('location')
            # uuid = self._sot.get.id(item='vlan', vid=vid, location=location)
            uuid = self._sot.get.vlans(vid=vid, location=location, get_single_id=True)
            if uuid:
                logger.debug(f'vlan vid={vid} location={location} found in nautobot')
            else:
                new_vlans.append(vlan)
        try:
            return self._nautobot.ipam.vlans.create(new_vlans)
        except Exception as exc:
            logger.error(exc)
        return False

    def _add_interfaces_to_nautobot(self, device, interfaces):
        """add interfaces to nautobot"""
        logger.debug(f'now adding {len(interfaces)} interfaces to device {device}')
        for interface in interfaces:
            if not 'device' in interface:
                interface['device'] = {'id': device.id}
            if 'lag' in interface:
                interface['lag']['device'] = device.id
        if self._bulk:
            try:
                return self._nautobot.dcim.interfaces.create(interfaces)
            except Exception as exc:
                if 'The fields device, name must make a unique set' in str(exc):
                    logger.error(f'one or more interfaces were already in nautobot')
                else:
                    logger.error(f'got exception: {exc}')
                return False
        else:
            for interface in interfaces:
                success = True
                try:
                    # if one request failes we return False
                    success = success and self._nautobot.dcim.interfaces.create(interface)
                except Exception as exc:
                    if 'The fields device, name must make a unique set' in str(exc):
                        logger.error(f'this interfaces is already in nautobot')
                    success = False
            return success

    def _add_prefix_to_nautobot(self, ip_addresses):
        """add prefix to nautobot"""
        added_prefixe = []

        for ipaddress in ip_addresses:
            parent = ipaddress.get('parent')
            if not parent:
                success = False
            properties = {
                'prefix': parent.get('prefix'),
                'namespace': parent.get('namespace',{}).get('name'),
                'status': {'name': 'Active'}
            }
            try:
                added_prefixe.append(self._nautobot.ipam.prefixes.create(properties))
            except Exception as exc:
                logger.error(f'could not add prefix to nautobot; got {exc}')

        return added_prefixe            

        # do we still need this code?
        # if not '/' in ipv4:
        #     logger.error(f'cannot add prefix to nautobot; no mask found in primary_ipv4')
        # ip = IPNetwork(ipv4)

        # logger.debug(f'network={ip.network} prefixlen={ip.prefixlen}')
        # properties = {'prefix': f'{ip.network}/{ip.prefixlen}',
        #               'status': {'name': 'Active'}}

        # try:
        #     return self._nautobot.ipam.prefixes.create(properties)
        # except Exception as exc:
        #     logger.error(exc)
        # return False

    def _add_ipaddress_to_nautbot(self, device, addresses):
        """add IP adrdress(es) to nautobot"""
        added_addresses = []

        # mandatory parameters are address, status and namespace
        # we get the hldm (or part of it)
        for address in addresses:
            ip_address = address.get('address')
            status = address.get('status', {'name': 'Active'})
            namespace = address.get('parent',{}).get('namespace',{}).get('name','Global')
            description = address.get('description')

            properties = {'address': ip_address,
                          'status': status,
                          'namespace': namespace}
            if description:
                properties.update({'description': description})
            if 'role' in address and address['role']:
                properties.update({'role': address['role']})
            if 'tags' in address and len(address['tags']) > 0:
                properties.update({'tags': address['tags']})
            try:
                added_addresses.append(self._nautobot.ipam.ip_addresses.create(properties))
                logger.debug(f'added IP {ip_address} to nautobot')
            except Exception as exc:
                if 'duplicate key value violates unique constraint' in str(exc):
                    logger.debug(f'IP {ip_address} namespace: {namespace} address already exists; return_ip={self._use_ip_if_already_exists}')
                    if self._use_ip_if_already_exists:
                        addr = self._nautobot.ipam.ip_addresses.get(address=ip_address.split('/')[0], namespace=namespace)
                        logger.debug(f'got IP {addr}')
                        added_addresses.append(addr)
                else:
                    logger.error(exc)
        return added_addresses 

    def _assign_ipaddress_to_interface(self, device, interface, ip_address):
        """assign IPv4 address to interface of device and set primary IPv4"""
        logger.debug(f'assigning IP {ip_address} to {device}/{interface.display}')
        try:
            properties = {'interface': interface.id,
                          'ip_address': ip_address.id} 
            assigned = self._nautobot.ipam.ip_address_to_interface.create(properties)
        except Exception as exc:
            if 'The fields interface, ip_address must make a unique set.' in str(exc):
                logger.debug(f'this IP address is already assigned')
                assigned = True
            else:
                assigned = False
                logger.error(exc)
        
        if assigned and str(interface.display).lower() == self._primary_interface.lower():
            logger.debug(f'found primary IP; update device and set primary IPv4')
            try:
                update = device.update({'primary_ip4': ip_address.id})
            except Exception as exc:
                logger.error(f'could not set primary IPv4 on {device}')

        return assigned

    def _remove_all_assignments(self, device, interface):
        """remove all assignments of any IP"""

        logger.debug(f'removing ALL assigments on {device.display}/{interface.display}')
        ip_addresses = self._nautobot.ipam.ip_addresses.filter(device_id=[device.id], interfaces=interface.display)
        for ip in ip_addresses:
            id_list = self._nautobot.ipam.ip_address_to_interface.filter(
                interface=interface.display, 
                ip_address=ip.id)
            response = True
            for assignment in id_list:
                try:
                    assignment.delete()
                except Exception as exc:
                    logger.error(exc)
                    response = False
        return response
