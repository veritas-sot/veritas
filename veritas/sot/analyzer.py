import logging
import os
import json
import yaml
import glob
import re
from veritas.tools import tools
from collections import defaultdict
from pybatfish.client.session import Session
from pybatfish.question.question import load_questions


class Analyzer(object):

    def __init__(self, sot=None, device_name=None):
        if not sot or not device_name:
            logging.error('sot and device are mandatory')
            return None

        logging.debug(f'Creating ANALYZER object')
        self._sot = sot
        self._device = device_name
        self._bf = None
        self._network = None
        self._snapshot = None
        self._analyzer_config = {}

        self._sot_config = sot.get_config()
        filename = "%s/%s" % (
            os.path.abspath(os.path.dirname(__file__)),
            self._sot_config['analyzer'].get('config') 
        )
        with open(filename) as f:
            self._analyzer_config = yaml.safe_load(f.read())

        # how to connect to batfish
        self._bf_address = self._analyzer_config['batfish'].get('bf_address')
        # the directory where the configs are stored
        self._snapshot_path = self._analyzer_config['batfish'].get('snapshot')

        logging.debug(f'setting bf_address: {self._bf_address} snapshot_apth: {self._snapshot_path}')        
        logging.debug('Setting host to connect')
        self._bf = Session(host=self._bf_address)
        if self._network:
            self._bf.set_network(self._network)

        logging.debug('Loading configs and questions')
        if self._snapshot:
            self._bf.init_snapshot(self._snapshot_path, snapshot=self._snapshot, overwrite=True)
        else:
            self._bf.init_snapshot(self._snapshot_path, overwrite=True)

        logging.getLogger("pybatfish").setLevel(logging.INFO)

        load_questions()

    def inf_defaultdict(self):
        return defaultdict(self.inf_defaultdict)

    def device(self, device_name):
        self._device = devicename
    
    def network(self, network):
        self._network = network
    
    def snapshot(self, snapshot):
        self._snapshot = snapshot

    def _get_config(self):
        src_dir = self._analyzer_config['configs'].get('devices')
        filename = "%s/%s" % (src_dir, self._device)
        with open(filename) as f:
            return f.read()
    
    def get_init_issues(self):
       return self._bf.q.initIssues().answer().frame()

    def analyse(self):
        logging.debug('running questions')
        devices_properties = self._bf.q.nodeProperties().answer().frame()
        interfaces = self._bf.q.interfaceProperties().answer().frame()
        filtered = interfaces[interfaces.apply(lambda row: row["Interface"].hostname == self._device, axis=1)]
        print(filtered[['Interface', 'Primary_Network']])
        # print(filtered)

        # hsrp_properties = self._bf.q.hsrpProperties().answer().frame()
        # ospf_properties = self._bf.q.ospfProcessConfiguration().answer().frame()
        # ospf_interfaces = self._bf.q.ospfInterfaceConfiguration().answer().frame()
        # ospf_areas = self._bf.q.ospfAreaConfiguration().answer().frame()
        # mlags = self._bf.q.mlagProperties().answer().frame()
        # ip_owners = self._bf.q.ipOwners().answer().frame()
        # vlans = self._bf.q.switchedVlanProperties().answer().frame()

        # my_interface_properties = filtered.to_json()
        # my_interfaces = json.loads(my_interface_properties)
        # my_device_properties = devices_properties.to_json()
        # my_devices = json.loads(my_device_properties)
        # print(json.dumps(my_devices, indent=4))
        # print('---')
        # print(json.dumps(my_interfaces, indent=4))
    