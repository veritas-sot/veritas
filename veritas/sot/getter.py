import logging
import requests
import json
import itertools
from pynautobot import api
from ..tools import tools


class Getter(object):

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
        
        device = properties.get('device')
        select = ['id','hostname','interfaces','location','primary_ip4','role',
                  'device_type','platform','tags','serial','config_context','cf']
        using = 'nb.devices'
        where = {'name': device}
        return self.query(select=select, using=using, where=where)
    
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
        pass

    def custom_fields_type(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(unnamed, named)

        response = {}

        self._nautobot = self._sot.open_nautobot()
        cf_types = self._nautobot.extras.custom_fields.all()
        for t in cf_types:
            response[t.display] = {'type': str(t.type)}
        return response

    def query(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(unnamed, named)

        select = properties.get('values') if 'values' in properties else properties.get('select',['hostname'])
        using = properties.get('using','nb.devices')
        where = properties.get('parameter') if 'parameter' in properties else properties.get('where')
    
        logging.debug(f'query select {select} using {using} where {where} {properties.get("normalize", False)}')
        response = self._execute_query(select=select, 
                                       using=using, 
                                       where=where)
        if properties.get('normalize', False):
            return self._normalize_response(properties, response)
        else:
            return response

    def _execute_query(self, *unnamed, **named):
        """execute query and returns data"""

        self._nautobot = self._sot.open_nautobot()

        query_final_vars = []
        query_final_params = []
        cf_fields_types = None

        properties = tools.convert_arguments_to_properties(unnamed, named)
        query_select = properties.get('select',{})
        using = properties.get('using', 'nb.devices')
        query_where = properties.get('where',{})
        normalize = properties.get('normalize', False)

        query = self._sot.get_config().get('queries',{}).get(using)

        # query_where are vars the user filters on (WHERE clause)
        for where in dict(query_where):
            # custom fields are a special case
            # we do NOT know what custom fields are part of the SOT
            if where.startswith('cf_'):
                if not cf_fields_types:
                    cf_fields_types = self.get.custom_fields_type()
                # SELECT custom fields
                query_where['get_cf'] = True
                cf_type = "String"
                if where.replace('cf_','') in cf_fields_types:
                    c = cf_fields_types[p.replace('cf_','')]['type']
                cf_type = "String" if c == "Text" else "List"
                if cf_type == "String":
                    query_final_vars.append(f'${where}: String')
                else:
                    query_final_vars.append(f'${where}: [String]')
            else:
                if where in ['within_include', 'changed_object_type', 'prefix']:
                    query_final_vars.append(f'${where}: String')
                elif where in ['vid']:
                    query_final_vars.append(f'${where}: [Int]')
                else:
                    query_final_vars.append(f'${where}: [String]')
            # add parameter to query parameters
            query_final_params.append(f'{where}: ${where}')

        # convert string ["val1","val2",....,"valn"] to list
        for key,val in dict(query_where).items():
            if '[' in val and ']' in val:
                # remove [,],' and "
                val = val.replace('[','').replace(']','').replace('"','').replace('\'','')
                query_where[key] = val.split(',')

        str_final_vars = ",".join(query_final_vars)
        str_final_params = ",".join(query_final_params)
        query = query.replace('__query_vars__', str_final_vars).replace('__query_params__',str_final_params)
        # logging.debug(query)
        # query_select are values the user has SELECTed
        for v in query_select:
            query_where[f'get_{v}'] = True

        logging.debug(f'query_select={query_select} using={using} query_where={query_where} normalize={normalize}')
        response = self._nautobot.graphql.query(query=query, variables=query_where).json
        if 'errors' in response:
            logging.error(f'got error: {response.get("errors")}')
            response = {}
        if 'nb.ipadresses' in using:
            data = dict(response)['data']['ip_addresses']
        elif 'nb.vlan' in using:
            data = dict(response)['data']['vlans']
        elif 'nb.prefixes' in using:
            data = dict(response)['data']['prefixes']
        elif 'nb.general' in using:
            data = dict(response)['data']
        elif 'nb.changes' in using:
            data = dict(response)['data']['object_changes']
        else:
            data = dict(response).get('data',{}).get('devices',{})
        return data