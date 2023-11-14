import logging
from ..tools import tools


class Checkmk:

    def __init__(self, sot, *values):
        self._sot = sot
        self.__api_url = None
        self.__session = None

    def start_session(self, *unnamed, **named):
        """starts checkMK session"""
        if not self._checkmk:
            return self._checkmk

        properties = tools.convert_arguments_to_properties(*unnamed, **named)

        # baseurl http://hostname/site/check_mk/api/1.0
        url = properties.get('url')
        site = properties.get('site')
        username = properties.get('username')
        password = properties.get('password')
        self.__api_url = "%s/%s/check_mk/api/1.0" % (url, site)

        logging.debug(f'starting session for {username} on {api_url}')
        self._check_mk = self._sot.rest(url=api_url, 
                                        username=username,
                                        password=password)
        check_mk.session()
        check_mk.set_headers({'Content-Type': 'application/json'})
        return self._check_mk

    def get_all_hosts(self):
        devicelist = []

        # get a list of all hosts of check_mk
        response = self._check_mk.get(url=f"/domain-types/host_config/collections/all",
                                      params={"effective_attributes": False, },
                                      format='object')
        if response.status_code != 200:
            logging.error(f'got status code {all_check_mk_hosts.status_code}; giving up')
            return []
        devices = response.json().get('value')
        for device in devices:
            devicelist.append({'host_name': device.get('title'),
                               'folder': device.get('extensions',{}).get('folder'),
                               'ipaddress': device.get('extensions',{}).get('attributes',{}).get('ipaddress'),
                               'snmp': device.get('extensions',{}).get('attributes',{}).get('snmp_community'),
                               'extensions': device.get('extensions',{})
                              })
        return devicelist

    def get_all_host_tags(self):
        host_tags = {}
        response = self._check_mk.get(url=f"/domain-types/host_tag_group/collections/all")
        for tag in response.json().get('value'):
            del tag['links']
            host_tag = tag.get('id',{})
            host_tags[host_tag] = tag.get('extensions',{}).get('tags')
        
        return host_tags

    def get_host(self, host):
        params={"effective_attributes": False}
        response = check_mk.get(url=f"/objects/host_config/{host}", params=params)
        if response.status_code == 404:
            return None, None
        return response.headers.get('ETag'), response.json()

    def add_to_check_mk(self, devices):
        data = {"entries": devices }
        params={"bake_agent": False}
        host = self._check_mk.post(url=f"/domain-types/host_config/actions/bulk-create/invoke",
                                   json=data, 
                                   params=params)
        status = host.status_code
        if status == 200:
            logging.info(f'host added to check_mk')
        elif status == 500:
            logging.error(f'got status {status}; maybe host is already in check_mk')
        else:
            logging.error(f'got status {status}; error: {host.content}')

    def activate_all_changes(self):
        logging.info('activating all changes')
        response = _activate_etag(check_mk, '*',[ site ])
        if response.status_code not in {200, 412}:
            logging.error(f'got status {response.status_code} could not activate changes; error: {response.content}')
            return None
        return True

    def _activate_etag(self, etag, site):
        headers={
                "If-Match": etag,
                "Content-Type": 'application/json',
            }
        data = {"redirect": False,
                "sites": site,
                "force_foreign_changes": True}

        return self._check_mk.post(url=f"/domain-types/activation_run/actions/activate-changes/invoke", 
                                   json=data, 
                                   headers=headers)

    def move_host_to_folder(hostname, etag, new_folder):
        data={"target_folder": new_folder}
        headers={
            "If-Match": etag,
            "Content-Type": 'application/json',
        }
        logging.debug(f'sending request {data} {headers}')
        response = self._check_mk.post(url=f"/objects/host_config/{hostname}/actions/move/invoke", 
                                       json=data,
                                       headers=headers)
        status = response.status_code
        if status == 200:
            logging.info('moved successfully')
            return True
        else:
            logging.error(f'status {status}; error: {response.content}')
            return False

    def update_host_in_cmk(self, hostname, etag, update_attributes, remove_attributes):
        logging.info(f'updating host {hostname}')
        data = {}
        if len(update_attributes) > 0:
            data.update({"update_attributes": update_attributes})
        if len(remove_attributes) > 0:
            data.update({"remove_attributes": remove_attributes})

        if len(data) == 0:
            logging.error(f'no update of {hostname} needed but update_host_in_cmk called')
            return

        headers={
            "If-Match": etag,
            "Content-Type": 'application/json',
        }
        logging.debug(f'sending request {data} {headers}')
        response = self._check_mk.put(url=f"/objects/host_config/{hostname}", 
                                      json=data,
                                      headers=headers)
        if response.status_code == 200:
            logging.info('updated successfully')
            return True
        else:
            logging.error(f'status {response.status_code}; error: {response.content}')
            return False

    def delete_hosts(self, devices):
        data = []
        for device in devices:
            data.append(device.get('host_name'))

        response = self._check_mk.post(url=f"/domain-types/host_config/actions/bulk-delete/invoke", json={'entries': data})
        if response.status_code == 200 or response.status_code == 204 :
            logging.info(f'hosts {data} successfully deleted')
            return True
        else:
            logging.error(f'error removing hosts; status {response.status_code}; error: {response.content}')
            return False

    def repair_services(self):

        devices = get_all_hosts()
        hosts_with_no_services = []
        for device in devices:
            hostname = device.get('host_name')
            params={
                "query": '{"op": "=", "left": "host_name", "right": "' + hostname + '"}',
                "columns": ['host_name', 'description'],
            }
            response = self._check_mk.get(url=f"/objects/host/{hostname}/collections/services", params=params)
            if response.status_code == 200 and len(response.json()['value']) <= 2:
                logging.info(f'host {hostname} has only {len(response.json()["value"])} services')
                hosts_with_no_services.append({'host_name': hostname})
        
        if len(hosts_with_no_services) > 0:
            self._start_single_discovery(check_mk_config, hosts_with_no_services, check_mk)

    def start_single_discovery(devices):
        logging.info('starting Host discovery')
        for device in devices:
            hostname = device.get('host_name')
            logging.info(f'starting discovery on {hostname}')
            # in cmk 2.2 you can add: 'do_full_scan': True,
            data = {'host_name': hostname, 
                    'mode': 'fix_all'}
            response = self._check_mk.post(url=f"/domain-types/service_discovery_run/actions/start/invoke", json=data)
            status = response.status_code
            if status == 200:
                logging.info('started successfully')
            else:
                logging.error(f'status {status}; error: {response.content}')

