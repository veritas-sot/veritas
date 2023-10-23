import logging
import requests
import json
import itertools
from pynautobot import api
from ..tools import tools


class Getter(object):

    query_fragments = {
        # devices
        'id': 'id',
        'hostname': 'hostname: name',
        'primary_ip4': 'primary_ip4 {address}',
        'location': 'location {name}',
        'role': 'role {name}',
        'device_type': 'device_type {model}',
        'platform': 'platform {name manufacturer {name}}',
        'tags': 'tags {name}',
        'serial': 'serial',
        'config_context': 'config_context',
        'custom_fields': 'custom_field_data: _custom_field_data',
        'interfaces': 'interfaces {\
              name\
              description\
              enabled\
              mac_address\
              type\
              mode\
              ip_addresses {\
                address\
                role { \
                    id \
                } \
                tags {\
                  name\
                }\
              }\
              connected_circuit_termination {\
                circuit {\
                  cid\
                  commit_rate\
                  provider {\
                    name\
                  }\
                }\
              }\
              tagged_vlans {\
                name\
                vid\
              }\
              untagged_vlan {\
                name\
                vid\
              }\
              cable {\
                termination_a_type\
                status {\
                  name\
                }\
                color\
              }\
              tags {\
                name\
              }\
              lag {\
                name\
                enabled\
              }\
              member_interfaces {\
                name\
              }\
            }',
        # general
        'vlans': 'vlans {vid name}',
        # prefixes
        'prefix': 'prefix',
        'description': 'description',
        'vlan': 'vlan {vid name}',
    }

    general_fragments = {
        'vlans': 'vlans (__device_string__) { id vid name location { name }}',
        'locations': 'locations (__device_string__) { id name }',
        'tags': 'tags (__device_string__) { id name content_types { id } }'
    }

    vlan_fragments = {
        'id': 'id',
        'vid': 'vid',
        'name': 'name',
        'description': 'description',
        'status': 'status {id name}',
        'tags': 'tags { name }',
        'role': 'role { name }',
        'location': 'location { name location_type { name } }',
        'vlan_group': 'vlan_group{ name }'
    }

    scope_id_to_name = {'3': 'dcim.device',
                        '4': 'dcim.interface',
                        '11': 'ipam.prefix'}

    def __new__(cls, sot):
        cls._instance = None
        cls._sot = None
        cls._nautobot = None
        cls._output_format = None
        cls._use = None
        cls._cache_dirty = True
        cls._cache = {'locations':{}, 'vlan': {}, 'tag': {}, 'device': {} }

        # singleton
        if cls._instance is None:
            logging.debug(f'Creating GETTER object')
            cls._instance = super(Getter, cls).__new__(cls)
            # Put any initialization here
            cls._sot = sot
        return cls._instance

    def __getattr__(self, item):
        if item == "as_object" or item == "as_obj":
            self._output_format = "obj"
        elif item == "as_json":
            self._output_format = "json"
        elif item == "as_dict":
            self._output_format = "dict"
        return self

    def _get_vlan(self, vid, site):
        logging.debug(f'getting vlan: {vid} / {site}')
        self._nautobot = self._sot.open_nautobot()

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

    # -----===== internal def =====-----


    # -----===== user command =====-----

    def device(self, name):
        """returns device"""
        self._nautobot = self._sot.open_nautobot()
        return self._nautobot.dcim.devices.get(name=name)

    def interface(self, *unnamed, **named):
        """returns interface of device"""
        properties = tools.convert_arguments_to_properties(unnamed, named)

        device = properties.get('device')
        device_id = properties.get('device_id')
        interface_name = properties.get('name')

        self._nautobot = self._sot.open_nautobot()

        if device_id:
            logging.debug(f'getting Interface {interface_name} of {device_id}')
            return self._nautobot.dcim.interfaces.get(device_id=device_id, 
                                                      name=interface_name)
        else:
            logging.debug(f'getting Interface {interface_name} of {device}')
            return self._nautobot.dcim.interfaces.get(device={'name': device}, 
                                                      name=interface_name)

    def interfaces(self, *unnamed, **named):
        """returns ALL interfaces of device"""
        properties = tools.convert_arguments_to_properties(unnamed, named)

        device = properties.get('device')
        device_id = properties.get('device_id')

        self._nautobot = self._sot.open_nautobot()

        if device_id:
            logging.debug(f'getting ALL Interface of {device_id}')
            return self._nautobot.dcim.interfaces.filter(device_id=device_id)
        else:
            logging.debug(f'getting ALL Interface of {device}')
            return self._nautobot.dcim.interfaces.filter(device=device)

    def use(self, use):
        # use another pattern instead of name__ie when query devices
        self._use = use
        return self

    def load_cache(self):
        all_tags = self._sot.select('tags') \
                         .using('nb.general') \
                         .normalize(False) \
                         .where()

        all_vlans = self._sot.select('id, vid, location') \
                         .using('nb.ipam.vlan') \
                         .normalize(False) \
                         .where()
        
        all_sites = self._sot.select('locations') \
                         .using('nb.general') \
                         .normalize(False) \
                         .where()

        for tag in all_tags['tags']:
            tag_id = tag['id']
            scopes = tag['content_types']
            name = tag['name']
            for scope in scopes:
                scope_id = scope['id']
                scope_name = self.scope_id_to_name.get(scope_id, scope_id)
                if scope_name not in self._cache['tag']:
                    self._cache['tag'][scope_name] = {}
                self._cache['tag'][scope_name][name] = tag_id

        for vlan in all_vlans:
            site = vlan.get('location',{}).get('name') if vlan.get('location') else "global"
            vlan_vid = vlan['vid']
            vlan_id = vlan['id']
            if site not in self._cache['vlan']:
                self._cache['vlan'][site] = {}
            self._cache['vlan'][site][vlan_vid] = vlan_id

        for site in all_sites['locations']:
            site_name = site.get('name')
            site_id = site.get('id')
            if site_name not in self._cache['locations']:
                self._cache['locations'][site_name] = {}
            self._cache['locations'][site_name] = site_id

        self._cache_dirty = False

    def _normalize_response(self, properties, data):
        """ 
        when using the cidr notation we have to use 'primary_ip4_for' to get the values
        """
        response = []
        for item in data:
            values = {}
            for key in properties.get('values',[]):
                if 'primary_ip4_for' in item:
                    if key.startswith('cf_'):
                        k = key.replace('cf_','')
                        values[k] = item.get('primary_ip4_for', {}).get('custom_field_data',{}).get(k)
                    else:
                        values[key] = item.get('primary_ip4_for', {}).get(key)
                else:
                    if key.startswith('cf_'):
                        k = key.replace('cf_','')
                        values[k] = item.get('custom_field_data',{}).get(k)
                    else:
                        values[key] = item.get(key)
            response.append(values)
        return response
        
    def hldm(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(unnamed, named)
        kc = self._sot.get_config()
        query = kc.get('nautobot',{}).get('hldm')
        return self._nautobot.graphql.query(query=query, 
                                            variables={'name': properties["device"]}).json
    
    def id(self, *unnamed, **named):
        """
        returns ID of device, site, vlan or tag
        this is used by our onboarding APP
        """
        if self._cache_dirty:
            self.load_cache()
        properties = tools.convert_arguments_to_properties(unnamed, named)

        self._nautobot = self._sot.open_nautobot()
        item = properties.get('item')
        del properties['item']
        logging.debug(f'getting id of {item}; parameter {properties}')

        if item == "device":
            hostname = properties.get('name')
            if hostname in self._cache['device']:
                logging.debug(f'getting id from cache')
                return self._cache['device'][hostname]
            try:
                device = self._nautobot.dcim.devices.get(**properties)
                if device:
                    logging.debug(f'adding {device.id} to cache')
                    self._cache['device'][hostname] = device.id
                    return device.id
                else:
                    logging.error(f'unknown device {hostname}')
                    return None
            except Exception as exc:
                logging.error(f'got exception {exc}')
                return None
        elif item == "site":
            site_name = properties.get('name')
            if site_name in self._cache['site']:
                logging.debug(f'getting id from cache')
                return self._cache['site'][site_name]
            try:
                site = self._nautobot.dcim.sites.get(**properties)
                if site:
                    logging.debug(f'adding {site.id} to cache')
                    self._cache['site'][site_name] = site.id
                    return site.id
                else:
                    logging.error(f'unknown site {site_name}')
                    return None
            except Exception as exc:
                logging.error(f'got exception {exc}')
                return None
        elif item =="vlan":
            vid = properties.get('vid')
            site_name = properties.get('site')
            id = self._cache['vlan'].get(site_name, {}).get(vid, None)
            if id:
                logging.debug(f'using cached id')
                return id
            else:
                vlan = self._get_vlan(vid, site_name)
                if vlan is None:
                    return None
                else:
                    if site_name not in self._cache['vlan']:
                        self._cache['vlan'][site_name] = {}
                    self._cache['vlan'][site_name][vid] = vlan.id
                    return vlan.id
        elif item =="tag":
            entity = properties.get('name')
            content_types = properties.get('content_types')
            id = self._cache['tag'].get(content_types, {}).get(entity, None)
            if id:
                logging.debug(f'using cached id')
                return id
            try:
                tag = self._nautobot.extras.tags.get(**properties)
                if tag:
                    logging.debug(f'adding {content_types} {tag.id} to cache')
                    self._cache['tag'][content_types] = tag.id
                    return tag.id
                else:
                    logging.error(f'unknown tag {entity}')
                    return None
            except Exception as exc:
                logging.error(f'got exception {exc}')
                return None

    def changes(self, *unnamed, **named):
        self._nautobot = self._sot.open_nautobot()

        properties = tools.convert_arguments_to_properties(unnamed, named)
        if 'start' in properties:
            properties['gt'] = properties.pop('start')
        if 'end' in properties:
            properties['lt'] = properties.pop('end')
        
        changes = self.query(name='changes', query_params=properties)

        if 'context_pattern' in properties:
            data = []
            search = properties.get('context_pattern','')
            for change in changes['data'].get('object_changes'):
                if search in change.get('change_context_detail'):
                    data.append(change)
            return data
        else:
            return changes['data'].get('object_changes')

    def query(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(unnamed, named)
        using = properties.get('using','nb.devices')
        values = properties.get('values',['hostname'])
        logging.debug(f'query using {using} ... with parameter {values} ... normalize {properties.get("normalize", False)}')
        response = self._advanced_query(values=values, 
                                        using=using, 
                                        parameter=properties.get('parameter'))
        if properties.get('normalize', False):
            return self._normalize_response(properties, response)
        else:
            return response

    def _advanced_query(self, *unnamed, **named):
        """
        advanced query
        we build a query by the parameter the user wants to have eg
        devices = sot.get.adv_query(values=['primary_ip4','site', 'interfaces'],
                                    parameter={'name': 'devicename', 'site': 'mysite'}) or
        devices = sot.get.adv_query(values=['custom_fields'],
                                    parameter={'cf_myfield': 'my_value'})
        """

        query_string = []
        device_string = []
        ipam_string = []
        general_string = []

        properties = tools.convert_arguments_to_properties(unnamed, named)
        query_params = properties.get('parameter',{})
        query_values = properties.get('values',{})
        normalize = properties.get('normalize', False)
        using = properties.get('using', 'nb.devices')

        logging.debug(f'using={using} query_params={query_params} query_values={query_values} normalize={normalize}')

        for key,value in dict(query_params).items():
            key0 = key.split('__')[0]
            logging.debug(f'key {key} value {value} (key0={key0})')
            query_params[key0] = value
            if key0 in ['vid']:
                query_params[key0] = int(value)
            if key.startswith('cf_'):
                    # if we use a lookup we have to use a list of strings
                    if '__list' in key:
                        key = key.replace('__list','')
                        device_string.append(f'{key}: ${key0}')
                        query_string.append(f'${key}: [String]')
                    elif '__' in key:
                        device_string.append(f'{key}: ${key0}')
                        query_string.append(f'${key0}: [String]')
                    else:
                        device_string.append(f'{key}: ${key0}')
                        query_string.append(f'${key0}: String')
            else:
                if 'nb.devices' in using and key in ['primary_ip4']:
                    query_string.append(f'${key}: String')
                    device_string.append(f'prefix: ${key}')
                elif key in ['primary_ip4']:
                    query_string.append(f'${key}: String')
                    device_string.append(f'parent: ${key}')
                elif key in ['within_include']:
                    query_string.append(f'${key}: String')
                    device_string.append(f'within_include: ${key}')
                elif key in ['vid','id']:
                    query_string.append(f'${key}: [Int]')
                    device_string.append(f'{key}: ${key}')
                elif key in ['prefix']:
                    query_string.append(f'${key}: String')
                    device_string.append(f'{key}: ${key}')
                else:
                    query_string.append(f'${key}: [String]')
                    device_string.append(f'{key}: ${key}')

        qstring= ",".join(query_string)
        dstring = ",".join(device_string)
        gstring = ",".join(general_string)

        if 'primary_ip4' in query_params:
            query = """query (__query_string__) {
                     ip_addresses(__device_string__) {
                       primary_ip4_for {
                         primary_ip4 {
                           address
                         }
                         __values__
                       }
                     }
                   }
                """
        elif 'nb.ipam.prefix' in using:
            query = """query (__query_string__) {
                        prefixes(__device_string__) {
                        __values__
                        }
                    }
                    """
        elif 'nb.ipam.vlan' in using:
            query = """query (__query_string__) {
                        vlans(__device_string__) {
                        __values__
                        }
                    }
                    """
        elif 'nb.general' in using:
            query = """query (__query_string__) {
                        __values_with_param__
                    }
                    """
        else:
            query = """query (__query_string__) {
                        devices(__device_string__) {
                        __values__
                        }
                    }
                    """

        # parse values and replace placehoder
        if 'nb.general' in using:
            for value in properties.get('values',[]):
                value = value.replace(' ','')
                fragment = self.general_fragments.get(value)
                if fragment is None:
                    logging.error(f'unknown query value "{value}"')
                else:
                    query = query.replace('__values_with_param__',f'{fragment} __values_with_param__')
        elif 'nb.ipam.vlan' in using:
            for value in properties.get('values',[]):
                value = value.replace(' ','')
                fragment = self.vlan_fragments.get(value)
                if fragment is None:
                    logging.error(f'unknown query value "{value}"')
                else:
                    query = query.replace('__values__',f'{fragment} __values__')
        else:
            for value in properties.get('values',[]):
                value = value.replace(' ','')
                if value.startswith('cf_') and 'custom_fields' not in query :
                    fragment = self.query_fragments.get('custom_fields')
                else:
                    fragment = self.query_fragments.get(value)
                if fragment is None:
                    logging.error(f'unknown query value "{value}"')
                else:
                    query = query.replace('__values__',f'{fragment} __values__')
    
        # replace all of our string now
        query = query.replace('__query_string__', qstring) \
                     .replace('__device_string__', dstring) \
                     .replace('__general_string__', gstring)

        # at last remove __values__ we are done
        query = query.replace('__values__','')
        query = query.replace('__values_with_param__','')

        self._nautobot = self._sot.open_nautobot()
        logging.debug(f'query: {query} variables {query_params}')
        response = self._nautobot.graphql.query(query=query, variables=query_params).json
        if 'errors' in response:
            logging.error(f'got error: {response.get("errors")}')
            response = {}

        if 'primary_ip4' in query_params:
            data = dict(response)['data']['ip_addresses']
        elif 'nb.ipam.vlan' in using:
            data = dict(response)['data']['vlans']
        elif 'nb.ipam.prefix' in using:
            data = dict(response)['data']['prefixes']
        elif 'nb.general' in using:
            data = dict(response)['data']
        else:
            data = dict(response).get('data',{}).get('devices',{})
        return data
