import logging
import requests
import json
import itertools
from pynautobot import api
from ..tools import tools


class Getter(object):

    query_fragments_v1 = {
        # devices
        'id': 'id',
        'hostname': 'hostname: name',
        'primary_ip4': 'primary_ip4 {address}',
        'site': 'site {name slug}',
        'device_role': 'device_role {name slug}',
        'device_type': 'device_type {model slug}',
        'platform': 'platform {name slug manufacturer {name}}',
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
                role\
                tags {\
                  slug\
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
                slug\
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

    query_fragments = {
        # devices
        'id': 'id',
        'hostname': 'hostname: name',
        'primary_ip4': 'primary_ip4 {address}',
        'site': 'site {name}',
        'device_role': 'device_role {name}',
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

    query_fragments_with_params_v1 = {
        'vlans': 'vlans (__general_string__) { id vid name site { name }}',
        'sites': 'sites (__general_string__) { id name slug }',
        'tags': 'tags (__general_string__) { id name slug content_types { id } }'
    }

    query_fragments_with_params = {
        'vlans': 'vlans (__general_string__) { id vid name site { name }}',
        'sites': 'sites (__general_string__) { id name }',
        'tags': 'tags (__general_string__) { id name content_types { id } }'
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
        cls._cache = {'site':{}, 'vlan': {}, 'tag': {}, 'device': {} }

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

    def use(self, use):
        # use another pattern instead of name__ie when query devices
        self._use = use
        return self

    def load_cache(self):
        all_tags = self._sot.select('tags') \
                         .using('nb.general') \
                         .normalize(False) \
                         .where()

        all_vlans = self._sot.select('vlans') \
                         .using('nb.general') \
                         .normalize(False) \
                         .where()
        
        all_sites = self._sot.select('sites') \
                         .using('nb.general') \
                         .normalize(False) \
                         .where()

        for tag in all_tags['tags']:
            slug = tag['slug']
            tag_id = tag['id']
            scopes = tag['content_types']
            for scope in scopes:
                scope_id = scope['id']
                # scope_id: 4 interface
                # scope_id: 3 device
                scope_name = self.scope_id_to_name.get(scope_id, scope_id)
                if scope_name not in self._cache['tag']:
                    self._cache['tag'][scope_name] = {}
                if self._sot.get_version() == 1:
                    self._cache['tag'][scope_name][slug] = tag_id
                else:
                    self._cache['tag'][scope_name][name] = tag_id

        for vlan in all_vlans['vlans']:
            site = vlan.get('site')
            if site:
                site_name = site['name']
            else:
                site_name = None
            vlan_vid = vlan['vid']
            vlan_name = vlan['name']
            vlan_id = vlan['id']
            if site_name not in self._cache['vlan']:
                self._cache['vlan'][site_name] = {}
            self._cache['vlan'][site_name][vlan_vid] = vlan_id

        for site in all_sites['sites']:
            site_name = site.get('name')
            site_id = site.get('id')
            if site_name not in self._cache['site']:
                self._cache['site'][site_name] = {}
            self._cache['site'][site_name] = site_id

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
    
    def id(self, **named):
        """
        returns ID of device, site, vlan or tag
        this is used by our onboarding APP
        """
        self._nautobot = self._sot.open_nautobot()
        item = named.get('item')
        del named['item']
        logging.debug(f'getting id of {item}; parameter {named}')

        if item == "device":
            hostname = named.get('name')
            if hostname in self._cache['device']:
                logging.debug(f'getting id from cache')
                return self._cache['device'][hostname]
            try:
                device = self._nautobot.dcim.devices.get(**named)
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
            site_name = named.get('name')
            if site_name in self._cache['site']:
                logging.debug(f'getting id from cache')
                return self._cache['site'][site_name]
            try:
                site = self._nautobot.dcim.sites.get(**named)
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
            vid = named.get('vid')
            site_name = named.get('site')
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
            if self._sot.get_version() == 1:
                entity = named.get('slug')
            else:
                entity = named.get('name')
            content_types = named.get('content_types')
            id = self._cache['tag'].get(content_types, {}).get(entity, None)
            if id:
                logging.debug(f'using cached id')
                return id
            try:
                tag = self._nautobot.extras.tags.get(**named)
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
        normalize = properties.get('normalize', False)
        using = properties.get('using', 'nb.devices')
        for key,value in dict(query_params).items():
            # logging.debug(f'key {key} value {value}')
            key0 = key.split('__')[0]
            query_params[key0] = value
            if key.startswith('cf_'):
                    device_string.append(f'{key}: ${key0}')
                    # if we use a lookup we have to use a list of strings
                    if '__' in key:
                        query_string.append(f'${key0}: [String]')
                    else:
                        query_string.append(f'${key0}: String')
            else:
                if 'primary_ip4' in key:
                    query_string.append(f'${key}: String')
                    device_string.append(f'parent: ${key}')
                elif 'nb.ipam' in using:
                    query_string.append(f'${key}: String')
                    device_string.append(f'{key}: ${key}')
                elif 'nb.general' in using:
                    query_string.append(f'${key}: [String]')
                    general_string.append(f'{key}: ${key}')
                else:
                    query_string.append(f'${key}:[String]')
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
        elif 'nb.ipam' in using:
            query = """query (__query_string__) {
                        prefixes(__device_string__) {
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
                fragment = self.query_fragments_with_params.get(value)
                if fragment is None:
                    logging.error(f'unknown query value "{value}"')
                else:
                    query = query.replace('__values_with_param__',f'{fragment} __values_with_param__')
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
        #logging.debug(f'query: {query} variables {query_params}')
        response = self._nautobot.graphql.query(query=query, 
                                                variables=query_params).json
        if 'primary_ip4' in query_params:
            data = dict(response)['data']['ip_addresses']
        elif 'nb.ipam' in using:
            data = dict(response)['data']['prefixes']
        elif 'nb.general' in using:
            data = dict(response)['data']
        else:
            data = dict(response)['data']['devices']
        return data

