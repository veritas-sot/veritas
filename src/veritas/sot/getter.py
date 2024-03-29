from loguru import logger
from pynautobot import models

# veritas
from veritas.sot import queries


class Getter(object):
    """Getter class to get properties from nautobot

    Parameters
    ----------
    sot : Sot
        the sot object
    """
    def __init__(self, sot):
        self._instance = None
        self._sot = sot
        self._nautobot = self._sot.open_nautobot()

    # -----===== user command =====-----

    def nautobot(self):
        """return nautobot object"""
        return self._nautobot

    def device(self, name:str, by_id:bool=False) -> models.dcim.Devices:
        """get device from nautobot

        Parameters
        ----------
        name : str
            name of the device
        by_id : bool, optional
            get device by id, by default False

        Returns
        -------
        device : Endppoint
            the device object
        """        
        # name can be either the name (in most cases) or the id

        if by_id:
            return self._nautobot.dcim.devices.get(id=name)
        else:
            return self._nautobot.dcim.devices.get(name=name)

    def device_by_ip(self, ip:str, cast:bool=False) -> models.dcim.Devices | str:
        """get device by using an ip address

        Parameters
        ----------
        ip : str
            ip address
        cast : bool, optional
            if true return name of device otherwise return Endpoint, by default False

        Returns
        -------
        device : Endpoint | str
            name or Endpoint of the device
        """        
        interfaces = self.query(select=['interfaces'], 
                                using='nb.ipaddresses',
                                where={'address': ip}, 
                                mode='sql')

        if interfaces and len(interfaces) > 0 and len(interfaces[0].get('interfaces', [])) > 0:
            device = interfaces[0].get('interfaces', {})[0].get('device',{}).get('name')
            logger.debug(f'found device in sot; device={device}')
            if cast:
                return device
            else:
                return self._nautobot.dcim.devices.get(name=device)
        return None

    def primary_ip4(self, name:str, cast:bool=False) -> models.ipam.IpAddresses | str:
        """get primary IP4 of the device

        Parameters
        ----------
        name : str
            name of the device
        cast : bool, optional
            if true return name of device otherwise Endpoint, by default False

        Returns
        -------
        device : Endpoint | str
            name of device or Endpoint
        """        
        device = self._nautobot.dcim.devices.get(name=name)
        if cast:
            return device.primary_ip4.display
        else:
            return device.primary_ip4

    def primary_ip6(self, name:str, cast:bool=False) -> models.ipam.IpAddresses | str:
        """get primary IP6 of the device

        Parameters
        ----------
        name : str
            name of the device
        cast : bool, optional
            if true return name of devie otherwise Endpoint, by default False

        Returns
        -------
        devide : models.ipam.IpAddresses | str
            name of device or Endpoint
        """        
        device = self._nautobot.dcim.devices.get(name=name)
        if cast:
            return device.primary_ip6.display
        else:
            return device.primary_ip6

    def address(self, address:str, by_id:bool=False) -> models.ipam.IpAddresses:
        """get address object by using its address or id

        Parameters
        ----------
        address : str
            address or id of the address
        by_id : bool, optional
            if true address is an id otherwise the representation of an ip, by default False

        Returns
        -------
        ipaddress : models.ipam.IpAddresses
            ipaddress object
        """        
        # name can be either the name (in most cases) or the id

        if by_id:
            return self._nautobot.ipam.ip_addresses.get(id=address)
        else:
            return self._nautobot.ipam.ip_addresses.get(address=address)

    def interface(self, device, interface_name, device_id=None):
        """returns interface of device"""
        if device_id:
            logger.debug(f'getting Interface {interface_name} of {device_id}')
            return self._nautobot.dcim.interfaces.get(device_id=device_id, 
                                                      name=interface_name)
        else:
            logger.debug(f'getting Interface {interface_name} of {device}')
            return self._nautobot.dcim.interfaces.get(device={'name': device}, 
                                                      name=interface_name)

    def interface_by_device_id(self,device_id:str, interface_name:str) -> models.dcim.Interfaces:
        """get uinterface by device id and interface name

        Parameters
        ----------
        device_id : str
            device id
        interface_name : str
            interface name

        Returns
        -------
        interface : models.dcim.Interfaces
            the interface object
        """
        logger.debug(f'getting Interface {interface_name} of {device_id}')
        return self._nautobot.dcim.interfaces.get(device_id=device_id, 
                                                    name=interface_name)

    def interfaces(self, device:str, device_id:str) -> models.dcim.Interfaces:
        """get all interfaces by device or device_id

        Parameters
        ----------
        device : str
            name of the device
        device_id : str
            device id

        Returns
        -------
        interfaces : models.dcim.Interfaces
            all interfaces of the device
        """        
        if device_id:
            logger.debug(f'getting ALL Interface of ID {device_id}')
            return self._nautobot.dcim.interfaces.filter(device_id=device_id)
        else:
            logger.debug(f'getting ALL Interface of {device}')
            return self._nautobot.dcim.interfaces.filter(device=device)

    def vlans(self,  *unnamed:list, **named:dict) -> list:
        """get vlans from nautobot

        This method calls the sot.ipam.get_vlans method

        Returns
        -------
        vlans : list
            a list of vlans
        """        
        return self._sot.ipam.get_vlans(*unnamed, **named)

    def hldm(self, device:str, get_id:bool=True) -> dict:
        """get HLDM (high level data model) of device

        Parameters
        ----------
        device : str
            name of the device
        get_id : bool, optional
            if true get id from device, by default True

        Returns
        -------
        dict
            the HLDM of the device
        """        
        # select ALL possible values
        select = ['asset_tag', 'custom_fields', 'config_context', 'device_bays',
                  'device_type','interfaces' , 'local_config_context_data', 
                  'location' , 'name', 'parent_bay', 'primary_ip4',
                  'platform', 'position', 'rack' , 'role', 'serial', 'status',
                  'tags', 'tenant']

        if get_id:
            select.append('id')

        using = 'nb.devices'
        where = {'name': device}
        return self.query(select=select, using=using, where=where)
    
    def changes(self, *unnamed, **named):
        pass

    def all_custom_fields_type(self, get_list:bool=False) -> dict | list:
        """return a list or dict of all custom_fields_type

        Parameters
        ----------
        get_list : bool, optional
            if true return list, by default False

        Returns
        -------
        custom_fields_type : dict | list
            list or dict of custom_fields_types
        """        
        cf_types = self._nautobot.extras.custom_fields.all()
        if get_list:
            return [str(t.type) for t in cf_types ]
        else:
            response = {}
            for t in cf_types:
                response[t.display] = {'type': str(t.type)}
            return response

    def all_device_types(self, get_list:bool=False) -> dict | list:
        """get a list or dict of all device types

        Parameters
        ----------
        get_list : bool, optional
            if true return list of device types, by default False

        Returns
        -------
        device_types : dict | list
            list or dict of device types
        """        
        device_types = self._nautobot.dcim.device_types.all()
        if get_list:
            return [t.model for t in device_types ]
        else:
            response = {}
            for t in device_types:
                response[t.display] = {'model': t.model}
            return response

    def get_all_roles(self, get_list:bool=False) -> dict | list:
        """get all roles from nautobot

        Parameters
        ----------
        get_list : bool, optional
            if true return list otherwise dict, by default False

        Returns
        -------
        roles : dict | list
            list or dict of roles
        """        
        roles = self._nautobot.extras.roles.all()
        if get_list:
            return [r.name for r in roles ]
        else:
            response = {}
            for r in roles:
                response[r.display] = {'name': r.name, 'content_types': r.content_types}
            return response

    def all_platforms(self, get_list:bool=False) -> dict | list:
        """return all platforms from nautobot

        Parameters
        ----------
        get_list : bool, optional
            if true return list of platforms, by default False

        Returns
        -------
        platforms : dict | list
            get list or dict of platforms
        """        
        platforms = self._nautobot.dcim.platforms.all()
        if get_list:
            return [p.name for p in platforms ]
        else:
            response = {}
            for p in platforms:
                response[p.display] = {'name': p.name}
            return response

    def all_locations(self, location_type:str=None, get_list:bool=False) -> dict | list:
        """return all locations (by location_type) from nautobot

        Parameters
        ----------
        location_type : str, optional
            location type, by default None
        get_list : bool, optional
            if true return list otherwise dict, by default False

        Returns
        -------
        locations : dict | list
            list or dict of locations
        """        
        locations = self._nautobot.dcim.locations.all()
        if get_list:
            return [loc.name for loc in locations if loc.location_type.name == location_type or not location_type]
        else:
            response = {}
            for loc in locations:
                if loc.location_type.name == location_type or not location_type:
                    row = {'name': loc.name, 
                                        'location_type': loc.location_type.name,
                                        'description': loc.description,
                          }
                    if loc and loc.parent and loc.parent.name:
                        row.update({'parent': loc.parent.name})
                    else:
                        row.update({'parent': None})
                    response[loc.name] = row
            return response

    def query(
            self, 
            select:list, 
            using:str, 
            where:str, 
            mode:str='sql', 
            transform:list=[],
            limit: int=0,
            offset: int=0) -> dict:
        """query nautobot

        Parameters
        ----------
        select : list
            the list of all values to get from nautobot
        using : str
            the name of the "table" to use
        where : str
            the where clause
        mode : str, optional
            either sql or gql (graphql), by default 'sql'
        transform : list, optional
            list of transformations, by default []
        limit : int, optional
            the number of items to get
        offset : int, optional
            the offset, by default 0

        Returns
        -------
        dict
            the resukt of the query


        This method calls either the sot.queries._execute_sql_query or the sot.queries._execute_gql_query method
        """        
        logger.bind(extra="query").debug(f'query select {select} using {using} where {where} (query)')
        if mode == "sql":
            return queries._execute_sql_query(
                self, 
                select=select, 
                using=using, 
                where=where, 
                transform=transform,
                limit=limit,
                offset=offset)
        else:
            return queries._execute_gql_query(self, select=select, using=using, where=where)

    def get_ipam_choices(self) -> dict:
        """return IPAM choices

        Returns
        -------
        choices : dict
            IPAM choices
        """        
        return self._nautobot.ipam.ip_addresses.choices()

    def get_interface_type_choices(self) -> dict:
        """return interface type choices

        Returns
        -------
        choices : dict
            Interface type choices
        """        
        return self._nautobot.dcim.interfaces.choices()

