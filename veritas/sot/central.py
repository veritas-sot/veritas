import logging
from pynautobot import api
from pynautobot.models.dcim import Interfaces
from pynautobot.models.dcim import Devices
from pynautobot.models.ipam import IpAddresses
from pynautobot.models.ipam import Prefixes
from pynautobot.core.response import Record


class Central(object):

    def __init__(self, sot):
        logging.debug(f'initializing central')
        self._nautobot = None
        self._sot = sot

    def open_nautobot(self):
        if self._nautobot is None:
            self._nautobot = api(self._sot.get_nautobot_url(), token=self._sot.get_token())

    def get_entity(self, func, title, getter):
        logging.debug("-- entering sot/central.py/get_entity")
        entity = None
        try:
            entity = func.get(**getter)
            if entity is None:
                logging.debug(f'entity not found in sot')
                return None
        except Exception as exc:
            logging.error(f'could not get entity; got exception {exc}')
            return None

        return entity

    def update_entity(self, func, properties, getter, convert_id=True):
        logging.debug("-- entering sot/central.py/update_entity")
        """
        func: used to get the updates entity
        properties: the new properties of the entity
        """

        # check if entity is part of sot
        try:
            # logging.debug(f'getter: {getter}')
            entity = func.get(**getter)
            if entity is None:
                logging.debug(f'entity not found in sot')
                return None
        except Exception as exc:
            logging.error(f'could not get entity; got exception {exc}')
            return None

        if convert_id:
            success, response = self.get_ids(properties)
            if not success:
                logging.error("could not convert items to IDs")
                return None
        try:
            success = entity.update(properties)
            if success:
                logging.debug("entity updated in sot")
            else:
                logging.debug("entity not updated in sot")
            return entity
        except Exception as exc:
            logging.error("entity not updated in sot; got exception %s" % exc)
            return None

        return entity

    def add_entity(self, func, properties, convert_id=False):
        logging.debug(f'-- entering central.py/add_entity')
        if convert_id:
            success, response = self.get_ids(properties)
            if not success:
                logging.error(f'could not convert items to IDs; response: {response}')
                logging.debug(f'-- leaving central.py/add_entity')
                return None
        try:
            item = func.create(properties)
            if item:
                logging.debug("entity added to sot")
            else:
                logging.debug("entity not added to sot")
            logging.debug(f'-- leaving central.py/add_entity')
            return item
        except Exception as exc:
            logging.error("entity not added to sot; got exception %s" % exc)
            logging.error(f'properties: {properties}')
            logging.debug(f'-- leaving central.py/add_entity')
            return None

    def delete_entity(self, func, title, message, getter):
        logging.debug("-- entering sot/central.py/delete_entity")
        message = dict(message)
        not_found = dict(message)
        not_found.update({'job': 'delete %s' % title,
                        'success': False,
                        'log': '%s not found in sot' % title
                        })
        deletetion_successfull = dict(message)
        deletetion_successfull.update({'job': 'delete %s' % title,
                                    'success': True,
                                    'log': '%s deleted in sot' % title,
                                    })

        deletetion_not_successfull = dict(message)
        deletetion_not_successfull.update({'job': 'delete %s' % title,
                                        'success': False,
                                        'log': '%s not deleted in sot' % title,
                                        })

        got_exception = dict(message)
        got_exception.update({'job': 'added %s' % title,
                                    'success': False,
                                    'log': 'error: got exception'
                            })

        # look if entity is in sot
        try:
            entity = func.get(**getter)
            if entity is None:
                logging.debug(f'{title} not found in sot')
                return None
        except Exception as exc:
            logging.error(f'could not get entity; got exception {exc}')
            return None

        # delete it
        try:
            success = entity.delete()
            if success:
                logging.debug("%s deleted from sot" % title)
            else:
                logging.debug("%s not deleted from sot" % title)
            return entity
        except Exception as exc:
            logging.error("%s not deleted from sot; got exception %s" %
                        (title, exc))
            got_exception.update({'exception': exc})
            return None

        # -----===== general methods =====-----

    def _get_vlan(self, vid, site):
        logging.debug("-- entering sot/central.py/_get_vlan")
        logging.debug(f'getting vlan: {vid} / {site}')
        self.open_nautobot()

        vlans = self._nautobot.ipam.vlans.filter(vid=vid)
        for vlan in vlans:
            try:
                site_name = vlan.site.name
            except Exception:
                site_name = None

            if site_name == site:
                return vlan

        logging.debug("no VLAN found")
        return None

    def get_ids(self, newconfig, convert_device_to_uuid=True, convert_interface_to_uuid=False):
        logging.debug("-- entering sot/central.py/get_ids")
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
