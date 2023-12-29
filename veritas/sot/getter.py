import requests
import json
import itertools
from loguru import logger
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

        # singleton
        if cls._instance is None:
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

    def _get_vlan(self, vid, location):
        logger.debug(f'getting vlan: {vid} / {location}')
        self._nautobot = self._sot.open_nautobot()

        vlans = self._nautobot.ipam.vlans.filter(vid=vid)
        for vlan in vlans:
            try:
                location_name = vlan.location.name
            except Exception:
                location_name = None

            if location_name == location:
                return vlan

        logger.debug("no VLAN found")
        return None

    # -----===== user command =====-----

    def nautobot(self):
        self._nautobot = self._sot.open_nautobot()
        return self._nautobot

    def device(self, name, by_id=False):
        """return device by using its name"""
        # name can be either the name (in most cases) or the id

        self._nautobot = self._sot.open_nautobot()
        if by_id:
            return self._nautobot.dcim.devices.get(id=name)
        else:
            return self._nautobot.dcim.devices.get(name=name)

    def device_by_ip(self, ip, cast=False):
        """return device by using its primary IP"""
        self._nautobot = self._sot.open_nautobot()
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

    def primary_ip4(self, name, cast=False):
        """return primary IP4 of the device"""
        self._nautobot = self._sot.open_nautobot()
        device = self._nautobot.dcim.devices.get(name=name)
        if cast:
            return device.primary_ip4.display
        else:
            return device.primary_ip4

    def primary_ip6(self, name, cast=False):
        """return primary IP6 of the device"""
        self._nautobot = self._sot.open_nautobot()
        device = self._nautobot.dcim.devices.get(name=name)
        if cast:
            return device.primary_ip6.display
        else:
            return device.primary_ip6

    def interface(self, *unnamed, **named):
        """returns interface of device"""
        properties = tools.convert_arguments_to_properties(unnamed, named)

        device = properties.get('device')
        device_id = properties.get('device_id')
        interface_name = properties.get('name')

        self._nautobot = self._sot.open_nautobot()

        if device_id:
            logger.debug(f'getting Interface {interface_name} of {device_id}')
            return self._nautobot.dcim.interfaces.get(device_id=device_id, 
                                                      name=interface_name)
        else:
            logger.debug(f'getting Interface {interface_name} of {device}')
            return self._nautobot.dcim.interfaces.get(device={'name': device}, 
                                                      name=interface_name)

    def interfaces(self, *unnamed, **named):
        """return ALL interfaces of device"""
        properties = tools.convert_arguments_to_properties(unnamed, named)

        device = properties.get('device')
        device_id = properties.get('device_id')

        self._nautobot = self._sot.open_nautobot()

        if device_id:
            logger.debug(f'getting ALL Interface of {device_id}')
            return self._nautobot.dcim.interfaces.filter(device_id=device_id)
        else:
            logger.debug(f'getting ALL Interface of {device}')
            return self._nautobot.dcim.interfaces.filter(device=device)

    def vlans(self,  *unnamed, **named):
        return self._sot.ipam.get_vlans(*unnamed, **named)

    def use(self, use):
        # use another pattern instead of name__ie when query devices
        self._use = use
        return self

    def hldm(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(unnamed, named)
        
        select = ['id','name','status','interfaces','location','primary_ip4',
                  'role', 'custom_field_data', 'device_type','platform','tags',
                  'serial', 'config_context', 'tenant']
        using = 'nb.devices'
        where = {'name': properties.get('device')}
        return self.query(select=select, using=using, where=where)
    
    def id(self, *unnamed, **named):
        """
        returns ID of device, site, vlan or tag
        this is used by our onboarding APP
        """

        properties = tools.convert_arguments_to_properties(unnamed, named)

        self._nautobot = self._sot.open_nautobot()
        item = properties.get('item')
        del properties['item']
        logger.debug(f'getting id of {item}; parameter {properties}')

        if item == "device":
            hostname = properties.get('name')
            try:
                device = self._nautobot.dcim.devices.get(**properties)
                if device:
                    return device.id
                else:
                    logger.error(f'unknown device {hostname}')
                    return None
            except Exception as exc:
                logger.error(f'got exception {exc}')
                return None
        elif item == "location":
            location_name = properties.get('name')
            try:
                location = self._nautobot.dcim.locations.get(**properties)
                if location:
                    return location.id
                else:
                    logger.error(f'unknown location {location_name}')
                    return None
            except Exception as exc:
                logger.error(f'got exception {exc}')
                return None
        elif item =="vlan":
            vid = properties.get('vid')
            location_name = properties.get('location')

            vlan = self._get_vlan(vid, location_name)
            print(vlan.description)
            if vlan:
                return vlan.id
            else:
                return None
        elif item =="tag":
            entity = properties.get('name')
            try:
                tag = self._nautobot.extras.tags.get(**properties)
                if tag:
                    return tag.id
                else:
                    return None
            except Exception as exc:
                logger.error(f'got exception {exc}')
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

        select = properties.get('select') if 'select' in properties else properties.get('values',['hostname'])
        using = properties.get('using','nb.devices')
        where = properties.get('where') if 'where' in properties else properties.get('parameter')
        mode = properties.get('mode','sql')

        logger.debug(f'query select {select} using {using} where {where} (query)')
        if mode == "sql":
            return self._execute_sql_query(select=select, using=using, where=where)
        else:
            return self._execute_gql_query(select=select, using=using, where=where)

    def _execute_sql_query(self, *unnamed, **named):
        """execute sql like query and returns data"""

        self._nautobot = self._sot.open_nautobot()

        subqueries = {'__interfaces_params__': [],
                      '__primaryip4for_params__': [],
                      '__devices_params__': [],
                      '__prefixes_params__': [],
                      '__changes_params__': [],
                      '__ipaddresses_params__': [],
                      '__vlans_params__': [],
                      '__locations_params__': [],
                      '__tags_params__': [],
                      '__general_params__': []}

        properties = tools.convert_arguments_to_properties(unnamed, named)
        select = properties.get('select',{})
        using = properties.get('using', 'nb.devices')
        where = properties.get('where',{})

        query = self._sot.get_config().get('queries',{}).get(using)

        # get final variables for our main parameter
        query_final_vars, cf_fields_types = self._dict_to_query_var(where, "")

        # loop through where statement and put values to subqueries and adjust custom field types
        for whr in where:
            #
            # we have some special cases
            # some queries have the possibility of "sub" queries eg. when you want to poll
            # devices within a specific prefix range that belong to a specific platform
            # primary_ip4_for(__primaryip4for_params__) is used to query for the platform
            #
            if whr.startswith('interfaces_'):
                subqueries['__interfaces_params__'].append(f'{whr.replace("interfaces_","")}: ${whr}')
            elif whr.startswith('pip4for_'):
                subqueries['__primaryip4for_params__'].append(f'{whr.replace("pip4for_","")}: ${whr}')
            else:
                sq = f'__{using.replace("nb.","")}_params__'
                subqueries[sq].append(f'{whr}: ${whr}')

            # adjust the type of custom fields
            name = f'${whr}: String'
            if isinstance(where[whr], list) and name in query_final_vars:
                logger.debug(f'convert {whr} to String')
                where[whr] = where[whr][0]

        # convert string ["val1","val2",....,"valn"] to list
        for key,val in dict(where).items():
            # logger.debug(f'key: {key} val: {val} type(val): {type(val)}')
            if isinstance(val, str):
                # convert Boolean to True/False
                if cf_fields_types and cf_fields_types.get(key.replace('cf_',''),{}).get('type') == 'Boolean (true/false)':
                    if 'true' in val.lower():
                        where[key] = True
                    else:
                        where[key] = False
            elif isinstance(val, list):
                # this is the only place where we can convert a list to a string
                # keys like prefix or within_include require a string
                # in this case we convert the list to a string
                # when we use simple queries we get the values as string
                # but using logical query we get the values as list
                #
                # when using a logical query we get the 'where' clause as list
                # in this case we have to convert the list to True/False if the custom_field
                # is of this type
                if key in ['within_include', 'changed_object_type', 'prefix']:
                    where[key] = val[0]
                # when using custom fields we have to convert the values as well
                elif cf_fields_types and cf_fields_types.get(key.replace('cf_',''),{}).get('type') == 'Text':
                    if len(val) > 1:
                        logger.erro(f'parameter {key} does not support [String]')
                    where[key] = val[0]
                elif cf_fields_types and cf_fields_types.get(key.replace('cf_',''),{}).get('type') == 'Boolean (true/false)':
                    if 'true' in val[0].lower():
                        where[key] = True
                    else:
                        where[key] = False

        str_final_vars = ",".join(query_final_vars)
        # the query variables
        query = query.replace('__query_vars__', str_final_vars)                     
        for q in subqueries:
            query = query.replace(q, ",".join(subqueries[q]))
        # cleanup
        query = query.replace('{}','').replace('()','')

        # select are values the user has SELECTed
        for v in select:
            if v.startswith('cf_'):
                where['get_custom_field_data'] = True
            else:
                where[f'get_{v}'] = True
        
        # debugging output
        # print('--- str_final_vars ---')
        # print(str_final_vars)
        # for q in subqueries:
        #     print(q)
        #     print(subqueries[q])
        # # print('--- query ---')
        # # print(query)
        # print('--- variables ---')
        # print(where)

        response = None
        logger.debug(f'select={select} using={using} where={where}')
        with logger.catch():
            response = self._nautobot.graphql.query(query=query, variables=where).json
        if not response:
            logger.error(f'got no valid response')
            return {}
        # logger.debug(response)
        if 'errors' in response:
            logger.error(f'got error: {response.get("errors")}')
            response = {}
        if 'nb.ipaddresses' in using:
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

    def _execute_gql_query(self, *unnamed, **named):
        """execute GraphQL based queries"""

        self._nautobot = self._sot.open_nautobot()
        variables = {}
        query_final_vars = []

        subqueries = {'__interfaces_params__': [],
                      '__primaryip4for_params__': [],
                      '__devices_params__': [],
                      '__prefixes_params__': [],
                      '__changes_params__': [],
                      '__ipaddresses_params__': [],
                      '__vlans_params__': [],
                      '__locations_params__': [],
                      '__tags_params__': [],
                      '__general_params__': []}

        properties = tools.convert_arguments_to_properties(unnamed, named)        
        select = properties.get('select',{})
        using = properties.get('using', 'nb.devices')
        where = properties.get('where', {})
        query = self._sot.get_config().get('queries',{}).get(using)

        for sq in where:
            prefix = f'{sq}_' if sq != 'devices' else ""
            qfv, cf_fields_types = self._dict_to_query_var(where[sq], prefix)
            query_final_vars += qfv
            sq_name = f'__{sq}_params__'
            for key,value in where[sq].items():
                subqueries[sq_name].append(f'{key}: ${prefix}{key}')
                variables[f'{prefix}{key}'] = value

        # select are values the user has SELECTed
        for v in select:
            if v.startswith('cf_'):
                variables['get__custom_field_data'] = True
            else:
                variables[f'get_{v}'] = True
        
        str_final_vars = ",".join(query_final_vars)
        # the query variables
        query = query.replace('__query_vars__', str_final_vars)                     
        for q in subqueries:
            query = query.replace(q, ",".join(subqueries[q]))
        # cleanup
        query = query.replace('{}','').replace('()','')

        # debugging output
        # print('--- str_final_vars ---')
        # print(str_final_vars)
        # for q in subqueries:
        #     print(q)
        #     print(subqueries[q])
        # print('--- query ---')
        # print(query)
        # print('--- variables ---')
        # print(variables)

        response = self._nautobot.graphql.query(query=query, variables=variables).json
        # logger.debug(response)
        if 'errors' in response:
            logger.error(f'got error: {response.get("errors")}')
            response = {}
        if 'nb.ipaddresses' in using:
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

    def _dict_to_query_var(self, data, prefix):
        """return list containing name of paramter and type of cf field types"""
        response = []
        cf_fields_types = None

        for whr in dict(data):
            # custom fields are a special case
            # we do NOT know what custom fields are part of the SOT
            cf_name = whr.replace('pip4for_','').replace('interfaces_','')
            if cf_name.startswith('cf_'):
                if not cf_fields_types:
                    cf_fields_types = self.get.custom_fields_type()

                # set default value to String
                cf_type = "String"
                if cf_name.replace('cf_','') in cf_fields_types:
                    cf_type = cf_fields_types[cf_name.replace('cf_','')]['type']

                if cf_type.lower() == "text":
                    response.append(f'${prefix}{whr}: String')
                elif cf_type == "Boolean (true/false)":
                    response.append(f'${prefix}{whr}: Boolean')
                else:
                    response.append(f'${prefix}{whr}: [String]')
            else:
                if whr in ['within_include', 'changed_object_type', 'prefix']:
                    response.append(f'${prefix}{whr}: String')
                elif whr in ['vid']:
                    response.append(f'${prefix}{whr}: [Int]')
                else:
                    response.append(f'${prefix}{whr}: [String]')
        return response, cf_fields_types
    