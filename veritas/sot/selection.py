import logging
import json
from functools import reduce
from boolean_parser import parse as boolean_parser
from boolean_parser.actions.clause import Condition
from boolean_parser.actions.boolean import BoolAnd, BoolOr
from ..tools import tools


class Selection(object):

    """
    SELECT hostname, primary_ip FROM nb.devices WHERE site=site
    SELECT site.name, site.slug FROM nb.sites
    SELECT hostname, primary_ip FROM nb.devices WHERE primary_ip=192.168.0.0/24

    # we always "JOIN" using hostnames (but really always!!!)
    SELECT hostname, site, veritas.status FROM nb.devices,veritas WHERE veritas.status=problem
    SELECT hostname FROM nb.devices,veritas WHERE veritas.uptime > 1year

    """

    # we cache the queries if we have logical expressions
    # because we get a list of hostnames using the expression
    # and then get return the cahced values
    query_cache = {}

    def __new__(cls, sot, *values):
        cls._instance = None
        cls._sot = None
        cls._using = set()
        cls._where = ""
        cls._normalize = False

        # singleton
        if cls._instance is None:
            logging.debug(f'Creating SELECTION object')
            cls._instance = super(Selection, cls).__new__(cls)
            # Put any initialization here
            cls._sot = sot

        # save values
        if len(values) > 1:
            cls._values = []
            for v in values:
                cls._values.append(v)
        else:
            for v in values:
                if isinstance(v, str):
                    cls._values = v.replace(' ','').split(',')
                elif isinstance(v, list):
                    cls._values = v

        return cls._instance

    def using(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        [self._using.add(x) for x in properties.split(',')]
        if 'nb.devices' in self._using and 'nb.ipam' in self._using:
            logging.warning(f'using devices and ipam in one query makes no sense')
        return self

    def normalize(self, normalize):
        self._normalize = normalize
        return self

    def where(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        logging.debug(f'query: values {self._values} using: {self._using} where {properties}')
        if 'nb.devices' in self._using:
            return self._adv_devices_query(values=self._values, expression=properties, normalize=self._normalize)
        if 'nb.ipam' in self._using:
            return self._general_query(values=self._values, 
                                       expression=properties,
                                       default={'prefix': ''},
                                       normalize=self._normalize)
        if 'nb.general' in self._using:
            return self._general_query(values=self._values, 
                                       expression=properties,
                                       default={'name': ''},
                                       normalize=self._normalize)
    
    def _general_query(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        expression = properties.get('expression')
        default = properties.get('default')
        if '=' in expression:
            key, value = expression.split('=')
            parameter = {key: value}
        else:
            parameter = default
        return self._sot.get.query(values=properties.get('values'),
                                   using=self._using,
                                   parameter=parameter,
                                   normalize=properties.get('normalize'))

    def _adv_devices_query(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(*unnamed, **named)

        expression = properties.get('expression')
        values = properties.get('values',['hostname'])
        logging.debug(f'expression {expression} ({len(expression)})')
        # lets check if we have a logical operation
        found_logical_expression = False
        try:
            if len(expression) > 0:
                res = boolean_parser(expression)
                lop = res.logicop
                # yes we have one ... parse it
                logging.debug(f'logical expression found {expression}')
                found_logical_expression = True
        except:
            logging.debug(f'no logical operation found ... simple call {expression}')

        if found_logical_expression:
            # we need the hostname in values
            if 'hostname' not in values:
                values.append('hostname')
            devices = self._exp_parser(res, values)
            response = []
            # now we have a list of all devices the user wants to have
            # we merge all devives and return the (normalized) response
            for device in devices:
                if device in self.query_cache:
                    response.append(self.query_cache[device])
                else:
                    logging.debug(f'host {device} not found in cache')
                    raw = self._sot.get.query(values=values,
                                              using=self._using,
                                              parameter={'name' : device},
                                              normalize=False)
                    self.query_cache[device] = raw[0]
                    response.append(raw[0])
        else:
            # found no logical expression to parse .... return simple advanced query
            if '=' in expression:
                key, value = expression.split('=')
                parameter = {key: value}
            else:
                parameter = {'name': ''}
            logging.debug(f'simple query using={self._using} values={values} parameter={parameter}')
            response = self._sot.get.query(values=values, using=self._using, parameter=parameter)
        
        # do we have to normalize the data
        if properties.get('normalize', False):
            return self._normalize_response(properties, response)
        else:
            return response

    def _exp_parser(self, cond, values):
        if isinstance(cond, Condition):
            logging.debug(f'final condition {cond} data: {cond.data}')
            return cond.data
        elif isinstance(cond, BoolAnd):
            return self._process_and_condition(cond, values)
        elif isinstance(cond, BoolOr):
            return self._process_or_condition(cond, values)
        else:
            logging.error(f'unknown type {type(cond)} {cond}')

    def _process_and_condition(self, cond, values):
        gpql_parameter = {}
        devices = []
        sot_devices = []
        got_list_as_result = False
        got_parameter = False

        # loop through all conditions. Either we get a list (expression contains (...) or
        # we get one (or more) "final condition". Those final conditions are used to buidl 
        # our query and get a list of devices
        for l in cond.conditions:
            response = self._exp_parser(l, values)
            if isinstance(response, list):
                got_list_as_result = True
                # we have a list of devices!
                logging.debug(f'got a list of devices {response} (and)')
                # merge the two lists together without duplicates
                devices.extend(x for x in response if x not in devices)
            else:
                # otherwise we got a string containing our final condition and 
                # we have to get the list of devices using this parameter
                gpql_parameter[response.get('parameter')] = response.get('value')
                got_parameter = True

        # do we have some graphql parameter to get a list of devices?
        if len(gpql_parameter) > 0:
            logging.debug(f'got gpql parameter {gpql_parameter}')
            sot_devices = self._get_devicelist_by_gpql_parameter(gpql_parameter, values)

        # at last we have to check which hostnames are in our devicelist and in our response
        if got_list_as_result and got_parameter:
            logging.debug(f'merging devices {devices} and latest sot_devices {sot_devices}')
            devicelist = list(reduce(lambda a, b: set(a) & set(b), [devices, sot_devices]))
        elif got_list_as_result:
            logging.debug(f'return the list of devices from our sub expression')
            # we got (one or more) lists of devices and no other request were done
            devicelist = devices
        else: 
            logging.debug(f'return the list of devices using the final conditions(s)')
            devicelist = sot_devices
         
        logging.debug(f'and {gpql_parameter} results in {devicelist}')
        return devicelist

    def _process_or_condition(self, cond, values):
        devices = set()
        gpql_parameter = []
        for l in cond.conditions:
            response = self._exp_parser(l, values)
            if isinstance(response, list):
                # we have a list of devices!
                logging.debug(f'got a list of devices {response} (or)')
                devices.update(response)
            else:
                # each final condition is used to get a list of devices
                gpql_parameter.append({response.get('parameter'): response.get('value')})

        if len(gpql_parameter) > 0:
            logging.debug(f'list of gpql parameter is {gpql_parameter}')
            # todo:
            # check if parameter like site is found twice
            for gpql in gpql_parameter:
                logging.debug(f'getting devices using parameter {gpql}')
                sot_devices = self._get_devicelist_by_gpql_parameter(gpql, values)
                for x in sot_devices:
                    devices.add(x)

            logging.debug(f'or {gpql_parameter} results in {devices}')
        return list(devices)

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
        
    def _get_devicelist_by_gpql_parameter(self, gpql, values):

        gpql_parameter = dict(gpql)
        sot_response = {}
        primary_response = {}
        primary_devices = None

        # get the devices using ALL but the primary_ip of our saved parameter
        if 'primary_ip4' in gpql_parameter:
            primary_stmnt = gpql_parameter['primary_ip4']
            del gpql_parameter['primary_ip4']
            primary_response = self._sot.get.query(values=values, 
                                                   parameter={'primary_ip4': primary_stmnt},
                                                   normalize=False)
            primary_devices = [ i['primary_ip4_for']['hostname'] for i in primary_response ]

        # if primary_ip was the only parameter gpql_parameter is 0
        if len(gpql_parameter) > 0:
            sot_response = self._sot.get.query(values=values, 
                                               parameter=gpql_parameter,
                                               normalize=False)
            # we only need one list but have a list of dicts containing hostnames
            sot_devices = [ i['hostname'] for i in sot_response ]
            # now do the AND if we have a primary_ip
            if primary_devices:
                devicelist = list(reduce(lambda a, b: set(a) & set(b), [primary_devices, sot_devices]))
            else:
                devicelist = sot_devices
        else:
            # only primary_ip
            devicelist = primary_devices

        # build cache
        # we use this cache to get the values later
        for device in sot_response:
            if device.get('hostname') in devicelist:
                self.query_cache[device.get('hostname')] = device

        for device in devicelist:
            for pr in primary_response:
                if device == pr.get('primary_ip4_for',{}).get('hostname'):
                    self.query_cache[device] = pr['primary_ip4_for']
   
        return devicelist
