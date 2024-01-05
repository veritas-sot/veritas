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
        namespace = properties.get('namespace','Global')
        logger.debug(f'getting IP {address} namespace {namespace}')
        return self._nautobot.ipam.ip_addresses.get(address=address,
                                                    namespace=namespace)

    def get_vlans(self, *unnamed, **named):
        """return a list of VLANs depending on the properties"""

        # the list of vlans to return
        response = []

        # get properties
        properties = tools.convert_arguments_to_properties(unnamed, named)

        vid = properties.get('vid')
        name = properties.get('name')
        location = properties.get('location','')
        location_type = properties.get('location_type')
        # if the user wants to get the id only (if one vlan)
        get_single_id = properties.get('get_single_id')
        # return objects
        get_obj = properties.get('get_obj')
        # the user can get other values; default is set
        select = properties.get('select', ['id', 'vid', 'name', 'location'])

        # set global_vid if user wants to see the global VLANs (without location)
        global_vid = False
        if location == '':
            location = None
        elif not location:
            location = None
            global_vid = True

        using = "nb.vlans"
        where = {'vid': vid, 'name': name}

        vlans = self._sot.get.query(select=select, using=using, where=where, mode='sql')

        # we have all VLANs 
        # unfortunately it is not possible to filter by location or location_type
        # we have to do it manually
        #
        # 1. user has set location and location_type
        # 2. user has set location only
        # 3. user has set location_type and location=None (root/Global)
        #    this case returns an empty set
        # 4. user has set location to None and has not set location_type
        # 5. user has neither set location nor location_type
        logger.debug(f'location: {location} location_type: {location_type} gloval_vid: {global_vid}')
        for vlan in vlans:
            vlan_location = vlan['location']
            if vlan_location:
                vlan_location_type = vlan['location']['location_type']
            else:
                vlan_location_type = None

            if location and location_type:
                if vlan_location and vlan['location'].get('name') == location and \
                   vlan['location']['location_type'].get('name') == location_type:
                   logger.debug(f'location and location_type match')
                   response.append(vlan)
            elif location:
                if vlan_location and vlan_location.get('name') == location:
                    logger.debug(f'location matches')
                    response.append(vlan)
            elif location_type and not global_vid:
                # this should aleway be false, or???
                if vlan_location and vlan_location_type.get('name') == location_type:
                    logger.debug(f'location_type matches')
                    response.append(vlan)
            elif not location_type and global_vid:
                logger.debug(f'global_vid is set')
                if not vlan_location: 
                    response.append(vlan)
            elif not location and not location_type:
                logger.debug(f'either location nor location_type set')
                response.append(vlan)

        # if get_single_id is set and we have only one item we return the id only
        if get_single_id and len(response) == 1:
            id = response[0].get('id')
            if get_obj:
                return self._nautobot.ipam.vlans.get(id=id)
            return id
        if get_obj:
            objs = []
            for vlan in response:
                id = vlan.get('id')
                objs.append(self._nautobot.ipam.vlans.get(id=id))
            return objs
        return response
