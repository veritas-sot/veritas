import os
import json
import yaml
from ..tools import tools
from collections import defaultdict
from ttp import ttp


class Configparser(object):

    def __init__(self, sot, *unnamed, **named):
        self._logger.debug(f'Creating CONFIGPARSER object')
        properties = tools.convert_arguments_to_properties(unnamed, named)
        self._sot = sot
        self._logger = sot.get_logger()
        self._device_config = properties.get('config', None)
        self._output_format = properties.get('output_format', 'json')
        self._empty_config = properties.get('empty_config', False)
        self._parser = None
        self._template = None
        self._template_filename = None
        self._sot_config = sot.get_config()
        self._could_not_parse = False
        filename = "%s/%s" % (
            os.path.abspath(os.path.dirname(__file__)),
            self._sot_config['configparser'].get('config') 
        )
        with open(filename) as f:
            self._my_config = yaml.safe_load(f.read())

        if not self.parse(*unnamed, **named):
            self._could_not_parse = True

    def could_not_parse(self):
        return self._could_not_parse

    def _get_template(self, properties):
        basedir = os.path.abspath(os.path.dirname(__file__))

        if self._template is not None:
            return self._template
        if 'template' in properties:
            return properties.get('template')

        if self._template_filename is None:
            platform = properties.get('platform','ios')
            # use default template that is configured in config
            filename = self._my_config.get('templates',{}).get(platform, None)
            self._logger.debug(f'using ttp template {filename}')
        else:
            filename = self._template_filename
        if filename is None:
            self._logger.error(f'please configure correct template filename for {platform}')
            return None
        try:
             with open("%s/%s" % (basedir, filename)) as f:
                ttp_template = f.read()
        except:
            self._logger.error(f'could not read template')
            return None
        
        return ttp_template

    def format(self, format):
        self._output_format = format
        return self

    def parse(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(unnamed, named)

        # get template
        ttp_template = self._get_template(properties)
    
        if self._device_config:
            device_config = self._device_config
        if 'config' in properties:
            device_config = properties.get('config')

        # create parser object and parse data using template:
        try:
            self._parser = ttp(data=device_config, template=ttp_template)
            self._parser.parse()
            self._parsed_config = self._parser.result(format='raw')[0]
            return True
        except Exception as exc:
            if self._empty_config:
                self._logger.debug(f'this is an empty config; return True')
                return True
            self._logger.error(f'could not parse config {exc}')
            return None

    def get(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(unnamed, named)

        format = properties.get('output_format', self._output_format)
        return self._parser.result(format=format)[0]

    def get_fqdn(self):
        """return FQDN of device"""
        domain = self._parsed_config[0].get('global', {}).get('fqdn',{}).get('domain_name',"")
        hostname = self._parsed_config[0].get('global', {}).get('fqdn',{}).get('hostname')
        if domain:
            return f'{hostname}.{domain}'
        else:
            return hostname

    def get_interface_name_by_address(self, address):
        interfaces = self._parsed_config[0].get('interfaces', {})
        ip = address.split('/')[0]
        for name, properties in interfaces.items():
            if ip == properties.get('ip'):
                self._logger.debug(f'found IP {ip} on {name}')
                return name
        return None
    
    def get_interface(self, interface):
        return self._parsed_config[0].get('interfaces', {}).get(interface, None)

    def get_interfaces(self):
        return self._parsed_config[0].get('interfaces', None)

    def get_ipaddress(self, interface):
        return self._parsed_config[0].get('interfaces', {}).get(interface, {}).get('ip', None)

    def get_vlans(self):
        global_vlans = []
        svi = []
        trunk_vlans = []

        for vid, properties in self._parsed_config[0].get('global',{}).get('vlan',{}).items():
            global_vlans.append({'vid': vid,
                                 'name': properties.get('name', 'unknown')})
    
        for name, properties in self._parsed_config[0].get('interfaces', {}).items():
            if 'vlan' in name.lower():
                svi.append({'vid': name[4:],
                            'name': properties.get('description','unkown')})
            if 'vlans_allowed' in properties:
                for vid in properties.get('vlans_allowed'):
                    trunk_vlans.append({'vid': vid,
                                        'name': 'trunked VLAN'})

        return global_vlans, svi, trunk_vlans

    def get_device_config(self):
        return self._device_config

    def get_section(self, section):
        response = []
        if section == "interfaces":
            found = False
            for line in self._device_config.splitlines():
                # find first occurence of the word interface at the beginning of the line
                if line.lower().startswith('interface '):
                    found = True
                    response.append(line)
                    continue
                if found and line.startswith(' '):
                    response.append(line)
                else:
                    found = False
        else:
            for line in self._device_config.splitlines():
                # check if line begins with 'section'
                if line.lower().startswith(section):
                    response.append(line)

        return response

    def get_global_config(self):
        response = []
        for line in self._device_config.splitlines():
            if line.lower().startswith('interface '):
                found = True
                continue
            elif not line.lower().startswith('interface '):
                found = False
            if not found:
                response.append(line)

        return response

    def find_in_global(self, properties):
        key = None
        value = None
        ignore_leading_spaces = False

        for k,v in properties.items():
            if 'match' in k:
                key = k
                value = v
            elif 'ignore_leading_spaces' == k:
                ignore_leading_spaces = v
    
        global_config = self.get_global_config()

        # the key can be match__ic etc.
        cmd = key.split('__')[0]
        if '__' in key:
            lookup = key.split('__')[1]

        self._logger.debug(f'cmd: "{cmd}" lookup: "{lookup}" value: "{value}" lines: {len(global_config)}')

        for line in global_config:
            if properties.get('ignore_leading_spaces'):
                src = line.lstrip()
            else:
                src = line

            if self._find_in_line(cmd, lookup, value, src):
                self._logger.debug(f'found pattern in global config')
                return True
        
        return False

    def find_in_interfaces(self, properties):
        key = None
        value = None
        ignore_leading_spaces = False

        for k,v in properties.items():
            if 'match' in k:
                key = k
                value = v
            elif 'ignore_leading_spaces' == k:
                ignore_leading_spaces = v
    
        interface_config = self.get_section('interfaces')

        # matched_on contains the list of all interfaces the value matched
        matched_on = []
        # the key can be match__ic etc.
        cmd = key.split('__')[0]
        if '__' in key:
            lookup = key.split('__')[1]

        self._logger.debug(f'cmd: "{cmd}" lookup: "{lookup}" value: "{value}" lines: {len(interface_config)}')

        for line in interface_config:
            if ignore_leading_spaces:
                src = line.lstrip()
            else:
                src = line

            if src.lower().startswith('interface '):
                interface = line[10:]
            
            if self._find_in_line(cmd, lookup, value, src):
                matched_on.append(interface)

        self._logger.debug(f'matched_on={matched_on}')
        return matched_on

# internals

    def _find_in_line(self, key, lookup, value, line):
        """
        n - not equal to (negation)
        ic - case-insensitive contains (*)
        c - case-sensitive contains (*)
        ie - case-insensitive exact match (*)

        nic - negated case-insensitive contains
        isw - case-insensitive starts-with
        nisw - negated case-insensitive starts-with
        iew - case-insensitive ends-with
        niew - negated case-insensitive ends-with
        nie - negated case-insensitive exact match
        re - case-sensitive regular expression match
        nre - negated case-sensitive regular expression match
        ire - case-insensitive regular expression match
        nire - negated case-insensitive regular expression match
        """

        # self._logger.debug(f'key: {key} lookup: {lookup} value: {value} line: {line}')
        if key == 'match':
            if lookup == "ie":
                # case-insensitive exact match
                if line.lower() == value.lower():
                    return True
            elif lookup == "ic":
                # case-insensitive contains
                if value.lower() in line.lower():
                    return True
            elif lookup == "c":
            # case-sensitive contains
                if value in line:
                    return True
            else:
                if line == value:
                    return True

        return False
