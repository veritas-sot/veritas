import logging
from pynautobot import api
from pynautobot.models.dcim import Interfaces
from pynautobot.models.dcim import Devices
from pynautobot.models.ipam import IpAddresses
from pynautobot.models.ipam import Prefixes
from pynautobot.core.response import Record


class Ipam(object):

    def __new__(cls, sot):
        cls._instance = None
        cls._last_attribute = None
        cls._sot = None
        cls._todos = {}
        cls._use_defaults = False
        cls._return_device = True
        cls._add_missing_ip = False

        cls._new_ipv4 = []
        cls._ipv4 = {'address': None, 'status': None}
        cls._ipv4_assignment = {'device': None,
                                'interface': None,
                                'interface_type': None,
                                'description': None}

        cls._ipv4_assignments = []
        if sot.get_version() == 2:
            cls._ipv4_defaults = {'status': {'name': 'Active'}}
        else:
            cls._ipv4_defaults = {'status': 'active'}

        cls._vlan_defaults = {}
        cls._prefix_defaults = {}

        cls._last_request = None
        cls._last_requested_ipv4 = None
        cls._last_requested_vlan = None
        cls._last_requested_prefix =  None
        cls._last_requested_site =  None

        # bulk operations
        cls._bulk = False
        cls._bulk_insert_ipv4_operation = []
        cls._bulk_insert_prefixe_operation = []
        cls._bulk_insert_vlan_operation = []

        # ip address to assign an interface
        cls._ipv4_assign_address = None
        cls._make_interface_primary = None

        # device or interface eg we assign an address to
        # device and interface is either a Device/Interface obj or a str
        cls._device = None
        cls._interface = None
        cls._site = None

        # connection to nautobot
        cls._nautobot = None
        # todo: check if we should use a singleton
        # we use a singleton pattern to ensure we have one
        # onboarding instance and not more
        if cls._instance is None:
            logging.debug(f'Creating IPAM object;')
            cls._instance = super(Ipam, cls).__new__(cls)
            # Put any initialization here
            cls._sot = sot

        return cls._instance

    # internal method 

    def open_nautobot(self):
        if self._nautobot is None:
            self._nautobot = api(self._sot.get_nautobot_url(), token=self._sot.get_token())
            self._nautobot.http_session.verify = self._sot.get_ssl_verify()

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

    # -----===== user commands =====-----

    def get(self):
        if self._last_request == "ipv4":
            return self.get_ipv4()
        if self._last_request == "vlan":
            return self.get_vlan()
        if self._last_request == "prefix":
            return self.get_prefix()

    def add(self, *unnamed, **named):
        logging.debug("-- entering sot/ipam.py/add")
        properties = self.__convert_arguments_to_properties(*unnamed, **named)
        if self._last_request == "ipv4":
            properties.update({'address': self._last_requested_ipv4})
            if self._bulk:
                self._bulk_insert_ipv4_operation.append(properties)
            else:
                return self.add_ipv4(properties)
        if self._last_request == "vlan":
            if self._bulk:
                self._bulk_vlan_ipv4_operation.append(properties)
            else:
                return self.add_vlan(properties)
        if self._last_request == "prefix":
            if self._bulk:
                self._bulk_insert_prefixe_operation.append(properties)
            else:
                return self.add_prefix(properties)

    def update(self, *unnamed, **named):
        logging.debug("-- entering sot/ipam.py/update")
        properties = self.__convert_arguments_to_properties(*unnamed, **named)
        if self._last_request == "ipv4":
            return self.update_ipv4(properties)
        if self._last_request == "vlan":
            return self.update_vlan(properties)
        if self._last_request == "prefix":
            return self.update_prefix(properties)
    
    def delete(self):
        if self._last_request == "ipv4":
            return self.delete_ipv4()
        if self._last_request == "vlan":
            return self.delete_vlan()
        if self._last_request == "prefix":
            return self.delete_prefix()

    def to(self, *kwargs):
        if self._last_attribute == "assign_interface":
            if isinstance(kwargs[0], IpAddresses) or isinstance(kwargs[0], str):
                self._ipv4_assign_address = kwargs[0]
                return self.assign_interface(self._ipv4_assign_address)
            else:
                logging.error("argument is either an interface nor an interface")
                self._ipv4_assign_address = None
                return None
        else:
            logging.error("unknown to; please fix code")

    def set_vlan_defaults(self, *unnamed, **named):
        logging.debug("-- entering sot/ipam.py/set_vlan_defaults")
        properties = self.__convert_arguments_to_properties(*unnamed, **named)

        logging.debug(f'setting VLAN defaults to {defaults}')
        self._vlan_defaults = defaults

    def set_ipv4_defaults(self,  *unnamed, **named):
        logging.debug("-- entering sot/ipam.py/set_ipv4_defaults")
        properties = self.__convert_arguments_to_properties(*unnamed, **named)

        logging.debug(f'setting IPv4 defaults to {properties}')
        self._ipv4_defaults = properties

    def set_prefix_defaults(self,  *unnamed, **named):
        logging.debug("-- entering sot/ipam.py/set_prefix_defaults")
        properties = self.__convert_arguments_to_properties(*unnamed, **named)

        logging.debug(f'setting PREFIX defaults to {properties}')
        self._prefix_defaults = properties

    def commit(self):
        logging.debug('-- entering ipam.py/commit')
        self.open_nautobot()

        if len(self._bulk_insert_ipv4_operation) > 0:
            logging.debug(f'adding {len(self._bulk_insert_ipv4_operation)} IP addresses(s)')
            try:
                nb_interface = self._nautobot.ipam.ip_addresses.create(self._bulk_insert_ipv4_operation)
                self._bulk_insert_ipv4_operation = []
            except Exception as exc:
                logging.error(f'could not add entity; got exception {exc}')

        if len(self._bulk_insert_vlan_operation) > 0:
            logging.debug(f'adding {len(self._bulk_insert_vlan_operation)} VLAN(s)')
            try:
                nb_interface = self._nautobot.ipam.vlans.create(self._bulk_insert_vlan_operation)
                self._bulk_insert_vlan_operation = []
            except Exception as exc:
                logging.error(f'could not add entity; got exception {exc}')

        if len(self._bulk_insert_prefixe_operation) > 0:
            logging.debug(f'adding {len(self._bulk_insert_prefixe_operation)} prefixe(s)')
            try:
                nb_interface = self._nautobot.ipam.prefixes.create(self._bulk_insert_prefixe_operation)
                self._bulk_insert_prefixe_operation = []
            except Exception as exc:
                logging.error(f'could not add entity; got exception {exc}')
                
    # -----===== attributes =====-----

    def device(self, device):
        if isinstance(device, Devices) or isinstance(device, str):
            logging.debug(f'setting device to {device}')
            self._device = device
        else:
            logging.error("wrong instance; please use Device or str")
            self._device = None
        return self

    def ipv4(self, ipv4):
        if isinstance(ipv4, IpAddresses) or isinstance(ipv4, str):
            logging.debug(f'setting _last_requested_ipv4 to {ipv4}')
            self._last_requested_ipv4 = ipv4
            self._last_request = "ipv4"
        else:
            logging.error("wrong instance; please use IpAddresses or str")
            self._last_requested_ipv4 = None
        return self

    def prefix(self, prefix):
        if isinstance(prefix, Prefixes) or isinstance(prefix, str):
            logging.debug(f'setting _last_requested_prefix to {prefix}')
            self._last_requested_prefix = prefix
            self._last_request = "prefix"
        else:
            logging.error("wrong instance; please use Prefixes or str")
            self._last_requested_prefix = None
        return self

    def vlan(self, vlan):
        if isinstance(vlan, Record) or isinstance(vlan, int):
            logging.debug(f'setting _last_requested_vlan to {vlan}')
            self._last_requested_vlan = vlan
            self._last_request = "vlan"
        else:
            logging.error("wrong instance; please use Record or int")
            self._device = None
        return self

    def use_defaults(self, use_defaults):
        logging.debug(f'setting use_defaults to {use_defaults} (ipam)')
        self._use_defaults = use_defaults
        return self

    def on(self, device):
        return self.device(device)

    def interface(self, interface):
        return self.assign(interface)

    def site(self, site):
        logging.debug(f'setting site to {site}')
        self._last_requested_site = site
        return self

    def assign(self, interface):
        if isinstance(interface, Interfaces):
            logging.debug(f'setting interface to {interface} (obj)')
            self._interface = interface
        elif isinstance(interface, str):
            logging.debug(f'setting interface to {interface} (str)')
            self._interface = interface
        else:
            logging.error(
                "wrong type (%s); please use Interface or str" % type(interface))
            self._interface = None
            return self
        self._last_attribute = "assign_interface"
        return self

    def return_device(self, return_device):
        # return_device == True: return device instead of error if device
        # is already part of sot
        logging.debug(f'setting _return_device to {return_device}')
        self._return_device = return_device
        return self

    def add_missing_ip(self, add_missing):
        logging.debug(f'setting _add_missing_ip to {add_missing}')
        self._add_missing_ip = add_missing
        return self

    def bulk(self, bulk):
        logging.debug('-- entering ipam.py/bulk')
        logging.debug(f'setting bulk to {bulk}')
        self._bulk = bulk
        return self

    # -----===== IP address management =====-----

    def get_ipv4(self):
        self.open_nautobot()
        logging.debug(f'getting IP address: {self._last_requested_ipv4}')

        if isinstance(self._last_requested_ipv4, str):
            return self._nautobot.ipam.ip_addresses.get(address=self._last_requested_ipv4)
        elif isinstance(self._last_requested_ipv4, IpAddresses):
            return self._last_requested_ipv4

    def add_ipv4(self, properties):
        # todo: checken ob address in properties
        # todo: check ob IP schon mit einer anderen CIDR in der sot ist
        self.open_nautobot()
        if self._use_defaults:
            logging.debug(f'adding default values to properties')
            properties.update(self._ipv4_defaults)

        logging.debug(f'add IP address: {properties}')
        success, error = self._convert_to_ids(properties)
        return self._nautobot.ipam.ip_addresses.create(properties)

    def delete_ipv4(self):
        self.open_nautobot()
        logging.debug(f'delete IP address: {self._last_requested_ipv4}')

        ipv4 = self._last_requested_ipv4

        if isinstance(ipv4, IpAddresses):
            getter = {'id': ipv4.id}
            message = {'address': ipv4.address}
        else:
            getter = {'address': ipv4}
            message = {'address': ipv4}

        # todo testen
        entity = self._nautobot.ipam.ip_addresses.get(**getter)
        entity.delete()

    def update_ipv4(self, properties):
        self.open_nautobot()
        logging.debug(f'update IP address: {properties}')

        if self._last_requested_ipv4:
            properties.update({'address': self._last_requested_ipv4})
            self._last_requested_ipv4 = None
        else:
            logging.error("no IP address specified; please use .ipv4() to specify address")
            return None

        entity = self._nautobot.ipam.ip_addresses.get(address=properties.get('address'))
        return entity.update(properties)

    # -----===== PREFIX management =====-----

    def get_prefix(self):
        self.open_nautobot()
        logging.debug(f'getting prefix: {self._last_requested_prefix}')

        if isinstance(self._last_requested_prefix, str):
            return self._nautobot.ipam.prefixes.get(prefix=self._last_requested_prefix)
        elif isinstance(self._last_requested_ipv4, Prefixes):
            return self._last_requested_prefix

    def add_prefix(self, properties):
        self.open_nautobot()
        if self._use_defaults:
            logging.debug(f'adding default values to properties')
            properties.update(self._prefix_defaults)

        if len(properties) > 0:
            properties.update({'prefix': self._last_requested_prefix})
        else:
            properties.update({'prefix': self._last_requested_prefix})

            if self._sot.get_version() == 2:
                properties.update({'status': {'name': 'Active'}})
            else:
                properties.update({'status': device_defaults['status']})

        logging.debug(f'add prefix: {properties}')

        success, error = self._convert_to_ids(device_properties)
        return self._nautobot.ipam.prefixes.create(properties)

    def delete_prefix(self):
        self.open_nautobot()
        properties = {'prefix': self._last_requested_prefix}

        entity = self._nautobot.ipam.prefixes.get(prefix=properties['prefix'])
        return entity.delete()

    def update_prefix(self, properties):
        self.open_nautobot()
        logging.debug(f'update prefix address: {properties}')

        if self._last_requested_prefix:
            properties.update({'prefix': self._last_requested_prefix})
            self._last_requested_prefix = None
        else:
            logging.error("no PREFIX specified; please use .prefix() to specify prefix")
            return None

        # update prefix in nautobot
        entity = self._nautobot.ipam.prefixes.get(prefix=properties.get('prefix'))
        return entity.update(properties)

    # -----===== VLAN management =====-----

    def get_vlan(self):
        self.open_nautobot()
        logging.debug(f'getting vlan: {self._last_requested_vlan} / {self._last_requested_site}')        

        if self._last_requested_vlan is None:
            logging.error("no VLAN specified; please use .vlan() to specify VLAN")
            return None
        elif isinstance(self._last_requested_vlan, Record):
            # strange ... user has specified vlan as Record. just return it. it should be already the vlan
            vlan = self._last_requested_vlan
            self._last_requested_vlan = None
            return vlan

        vlans = self._nautobot.ipam.vlans.filter(vid=self._last_requested_vlan)
        for vlan in vlans:
            try:
                site_name = vlan.site.name
            except Exception:
                site_name = None

            if site_name == self._last_requested_site:
                return vlan

        logging.debug("no VLAN found")
        return None

    def add_vlan(self, properties):
        logging.debug(f'-- entering ipam.py/add_vlan')
        self.open_nautobot()
        skip = False
        logging.debug(f'adding VLAN {self._last_requested_vlan} with properties {properties} to sot')
        if self._use_defaults:
            logging.debug(f'adding default values to properties')
            properties.update(self._vlan_defaults)

        if len(properties) > 0:
            properties.update({'vid': self._last_requested_vlan})
        else:
            properties.update({'vid': self._last_requested_vlan,
                               'name': 'vlan-%s' % self._last_requested_vlan})
            if self._sot.get_version() == 2:
                properties.update({'status': {'name': 'Active'}})
            else:
                properties.update({'status': device_defaults['status']})

        logging.debug(f'getting all vlans with vid {properties["vid"]}')
        vlans = self._nautobot.ipam.vlans.filter(vid=properties['vid'])
        for vlan in vlans:
            try:
                site_name = vlan.site
            except Exception:
                site_name = None

            logging.debug("checking vlan.vid %s / %s site_name: %s / %s" % \
                (vlan.vid, properties.get('vid'), site_name, properties.get('site')))
            if int(vlan.vid) == int(properties.get('vid')) and str(site_name) == str(properties.get('site')):
                logging.debug(f'VLAN already in sot')
                skip = True
            
        if not skip:
            message = {'vid': properties.get('vid'), 'site': properties.get('site')}

            success, error = self._convert_to_ids(device_properties)
            return self._nautobot.ipam.vlans.create(properties)

    def delete_vlan(self):
        self.open_nautobot()
        properties = {'vid': self._last_requested_vlan}

        # add site if user has configured it
        if self._last_requested_site:
                properties.update({'site':self._last_requested_site})

        if isinstance(properties, Record):
            vid = properties.vid
            site = properties.site.name
        else:
            vid = properties.get('vid')
            site = properties.get('site')

        vlans = self._nautobot.ipam.vlans.filter(vid=vid)
        for vlan in vlans:
            try:
                site_name = vlan.site.name
            except Exception:
                site_name = None

            if site_name == site:
                message = {'vid': vid, 'site':site_name}
                entity = self._nautobot.ipam.vlans.get(id=vlan.id)
                return entity.delete()

        logging.debug("no VLAN found")
        return None
        
    def update_vlan(self, properties):
        self.open_nautobot()
        logging.debug(f'update VLAN address: {properties}')

        if self._last_requested_vlan:
            properties.update({'vid': self._last_requested_vlan,
                               'site': self._last_requested_site})
            self._last_requested_vlan = None
            self._last_requested_site = None
        else:
            logging.error("no VLAN specified; please use .vlan() to specify VLAN")
            return None

        # there are global and site specific VLANs
        # if site is None it is a global one otherwise site specific
        vlans = self._nautobot.ipam.vlans.filter(vid=properties['vid'])
        for vlan in vlans:
            try:
                site_name = vlan.site
            except Exception:
                site_name = None

            if vlan.vid == properties.get('vid') and site_name == properties.get('site'):
                message = {'vid': properties.get('vid'), 'site': properties.get('site')}
                entity = self._nautobot.ipam.vlans.get(id=vlan.id)
                entity.update(properties)

        logging.debug("no VLAN found")
        return None

    # -----===== IP assignment management =====-----

    def assign_interface(self, ip_address):
        self.open_nautobot()
        logging.debug(f'prepare assignment of IP address: {ip_address}')

        if isinstance(ip_address, IpAddresses):
            nb_ipadd = self._nautobot.ipam.ip_addresses.get(id=ip_address.id)
        else:
            try:
                nb_ipadd = self._nautobot.ipam.ip_addresses.get(address=ip_address)
            except Exception as exc:
                logging.error("got multiple IP adresses; please fix config")
                return None

        if nb_ipadd is None:
            if self._add_missing_ip:
                logging.debug(f'unknown IP address {ip_address} adding it to sot')
                properties = {'address': ip_address,
                              'description': 'IP'}
                if self._sot.get_version() == 2:
                    properties.update({'status': {'name': 'Active'}})
                else:
                    properties.update({'status': device_defaults['status']})

                nb_ipadd = self.add_ipv4(properties)
                if nb_ipadd:
                    logging.debug(f'added IP {ip_address} to sot')
                else:
                    logging.error(f'could not add IP {ip_address} to sot; assignment not possible')
                    return None
            else:
                logging.error(
                    f'unknown IP address {ip_address} and _add_missing is False; assignment is not possible')
                return None
        logging.debug("got IP address %s" % nb_ipadd)

        if isinstance(self._device, Devices):
            nb_device = self._nautobot.dcim.devices.get(id=self._device.id)
        else:
            nb_device = self._nautobot.dcim.devices.get(name=self._device)

        logging.debug("got device %s" % nb_device)
        if nb_device is None:
            logging.error("unknown device")
            return None

        if isinstance(self._interface, Interfaces):
            nb_interface = self._nautobot.dcim.interfaces.get(id=self._interface.id)
        else:
            nb_interface = self._nautobot.dcim.interfaces.get(device_id=nb_device.id, name=self._interface)
        logging.debug("got interface %s" % nb_interface)

        if nb_interface is None:
            logging.error("unknown interface")
            return None

        # now we have the address, the interface and the device
        try:
            logging.debug(f'assign IP address %s to %s' % (
                ip_address,
                self._device))

            if self._sot.get_version() == 2:
                response = self._nautobot.ipam.ip_address_to_interface.create(
                    {"interface": nb_interface.id, 
                     "ip_address": nb_ipadd.id}
                )
            else:
                response = nb_ipadd.update({
                    'assigned_object_type': "dcim.interface",
                    'assigned_object_id': nb_interface.id})

            if response:
                logging.debug("IP address assigned")
                return response
            else:
                logging.debug("no update needed")
                return nb_ipadd
        except Exception as exc:
            logging.error("got exception %s" % exc)
            return None

        return True

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
