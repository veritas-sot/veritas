import logging
from ..tools import tools


class Checkmk:

    def __init__(self, sot, url, site, username, password):
        self._sot = sot
        self.__url = url
        self.__site = site
        self.__username = username
        self.__password = password
        self.__session = None
        self._checkmk = None
        self.__api_url = None
        self._start_session()

    def _start_session(self):
        """starts checkMK session"""
        logging.debug(f'starting checkmk session on {self.__api_url}')

        # baseurl http://hostname/site/check_mk/api/1.0
        api_url = f'{self.__url}/{self.__site}/check_mk/api/1.0'
        print(api_url)
        logging.debug(f'starting session for {self.__username} on {api_url}')
        self._checkmk = self._sot.rest(url=api_url, 
                                       username=self.__username,
                                       password=self.__password)
        self._checkmk.session()
        self._checkmk.set_headers({'Content-Type': 'application/json'})

    def get_all_hosts(self):
        """return a list of all hosts"""
        devicelist = []

        # get a list of all hosts of check_mk
        response = self._checkmk.get(url=f"/domain-types/host_config/collections/all",
                                     params={"effective_attributes": False, },
                                     format='object')
        if response.status_code != 200:
            logging.error(f'got status code {response.status_code}; giving up')
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
        response = self._checkmk.get(url=f"/domain-types/host_tag_group/collections/all")
        for tag in response.json().get('value'):
            del tag['links']
            host_tag = tag.get('id',{})
            host_tags[host_tag] = tag.get('extensions',{}).get('tags')
        
        return host_tags

    def get_etag(self, host):
        params={"effective_attributes": False}
        response = self._checkmk.get(url=f"/objects/host_config/{host}", params=params)
        if response.status_code == 404:
            return None
        return response.headers.get('ETag')

    def add_hosts(self, devices):
        data = {"entries": devices}
        params={"bake_agent": False}
        host = self._checkmk.post(url=f"/domain-types/host_config/actions/bulk-create/invoke",
                                  json=data, 
                                  params=params)
        status = host.status_code
        if status == 200:
            logging.debug(f'host added to check_mk')
            return True
        elif status == 500:
            logging.error(f'got status {status}; maybe host is already in check_mk')
            return False
        else:
            logging.error(f'got status {status}; error: {host.content}')
            return False

    def activate_all_changes(self):
        logging.debug('activating all changes')
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

        return self._checkmk.post(url=f"/domain-types/activation_run/actions/activate-changes/invoke", 
                                   json=data, 
                                   headers=headers)

    def move_host_to_folder(self, hostname, etag, new_folder):
        data={"target_folder": new_folder}
        headers={
            "If-Match": etag,
            "Content-Type": 'application/json',
        }
        logging.debug(f'sending request {data} {headers}')
        response = self._checkmk.post(url=f"/objects/host_config/{hostname}/actions/move/invoke", 
                                       json=data,
                                       headers=headers)
        status = response.status_code
        if status == 200:
            logging.debug('moved successfully')
            return True
        else:
            logging.error(f'status {status}; error: {response.content}')
            return False

    def update_host_in_cmk(self, hostname, etag, update_attributes, remove_attributes):
        logging.debug(f'updating host {hostname}')
        data = {}
        if update_attributes:
            data.update({"update_attributes": update_attributes})
        if remove_attributes:
            data.update({"remove_attributes": remove_attributes})

        if len(data) == 0:
            logging.error(f'no update of {hostname} needed but update_host_in_cmk called')
            return

        headers={
            "If-Match": etag,
            "Content-Type": 'application/json',
        }
        logging.debug(f'sending request {data} {headers}')
        response = self._checkmk.put(url=f"/objects/host_config/{hostname}", 
                                     json=data,
                                     headers=headers)
        if response.status_code == 200:
            logging.debug('updated successfully')
            return True
        else:
            logging.error(f'status {response.status_code}; error: {response.content}')
            return False

    def delete_hosts(self, devices):
        data = []
        for device in devices:
            data.append(device.get('host_name'))

        response = self._checkmk.post(url=f"/domain-types/host_config/actions/bulk-delete/invoke", json={'entries': data})
        if response.status_code == 200 or response.status_code == 204 :
            logging.debug(f'hosts {data} successfully deleted')
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
            response = self._checkmk.get(url=f"/objects/host/{hostname}/collections/services", params=params)
            if response.status_code == 200 and len(response.json()['value']) <= 2:
                logging.info(f'host {hostname} has only {len(response.json()["value"])} services')
                hosts_with_no_services.append({'host_name': hostname})
        
        if len(hosts_with_no_services) > 0:
            self._start_single_discovery(check_mk_config, hosts_with_no_services, check_mk)

    def start_single_discovery(self, devices):
        logging.debug('starting Host discovery')
        for device in devices:
            hostname = device.get('host_name')
            logging.info(f'starting discovery on {hostname}')
            # in cmk 2.2 you can add: 'do_full_scan': True,
            data = {'host_name': hostname, 
                    'mode': 'fix_all'}
            response = self._checkmk.post(url=f"/domain-types/service_discovery_run/actions/start/invoke", json=data)
            status = response.status_code
            if status == 200:
                logging.debug('started successfully')
                return True
            else:
                logging.error(f'status {status}; error: {response.content}')
                return False

    def update_folders(self, devices, default_config):
        for device in devices:
            fldrs = device.get('folder')
            response = self._checkmk.get(url=f"/objects/folder_config/{fldrs}")
            status = response.status_code
            if status == 200:
                logging.debug(f'{fldrs} found in check_mk')
            elif status == 404:
                # one or more parent folders are missing
                # we have to check the complete path
                logging.debug(f'{fldrs} does not exist; creating it')
                path = fldrs.split('~')
                for i in range(1, len(path)):
                    pth = '~'.join(path[1:i])
                    logging.debug(f'checking if ~{pth} exists')
                    response = self._checkmk.get(url=f"/objects/folder_config/~{pth}")
                    if response.status_code == 404:
                        logging.debug(f'{pth} does not exists')
                        i = pth.rfind('~')
                        name = pth[i+1:]
                        if i == -1:
                            parent = "~"
                        else:
                            parent = "~%s" % pth[0:i]
                        data = {"name": name, 
                                "title": name, 
                                "parent": parent }
                        folder_config = self.get_folder_config(default_config, name)
                        if folder_config is not None:
                            data.update({'attributes': folder_config})
                        logging.debug(f'creating folder {name} in {parent}')
                        response = self._checkmk.post(url=f"/domain-types/folder_config/collections/all", json=data)
                        if response.status_code == 200:
                            logging.debug(f'folder {name} added in {parent}')
                        else:
                            logging.error(f'could not add folder; error: {response.content}')
                # now we have the path upto our folder
                i = fldrs.rfind('~')
                name = fldrs[i+1:]
                if i == -1:
                    parent = "~"
                else:
                    parent = fldrs[0:i]
                logging.debug(f'creating folder {name} in {parent}')
                data = {"name": name, 
                        "title": name, 
                        "parent": parent }
                folder_config = self.get_folder_config(default_config, name)
                if folder_config is not None:
                            data.update({'attributes': folder_config})
                response = self._checkmk.post(url=f"/domain-types/folder_config/collections/all", json=data)
                if response.status_code == 200:
                    logging.debug(f'folder {name} added in {parent}')
                    return True
                else:
                    logging.error(f'could not add folder; error: {response.content}')
                    return False
            else:
                logging.debug(f'got status: {status}')
                return False

    def get_folder_config(self, folders_config, folder_name):
        default = None
        for folder in folders_config:
            if folder['name'] == folder_name:
                response = dict(folder)
                del response['name']
                return response
            elif folder['name'] == 'default':
                response = dict(folder)
                del response['name']
                default = response
        return default

    def add_folder(self, folder, default_config=None):
        name = folder.get('name')
        parent = folder.get('parent','')
        data = {"name": name,
                "title": folder.get('title', name),
                "parent": parent
               }
        folder_config = self.get_folder_config(default_config, name)
        if folder_config is not None:
            data.update({'attributes': folder_config})
        logging.debug(f'creating folder {name} in {parent}')
        response = self._checkmk.post(url=f"/domain-types/folder_config/collections/all", json=data)
        if response.status_code == 200:
            logging.info(f'folder {name} added in {parent}')
            return True
        else:
            logging.error(f'could not add folder; error: {response.content}')
            if response.status_code == 200:
                logging.info(f'folder {name} added in {parent}')
                return True
            else:
                logging.error(f'could not add folder; error: {response.content}')
                return False

    def add_config(self, config, url):
        response = self._checkmk.post(url=url, json=config)
        if response.status_code == 200:
            logging.info(f'adding config successfully')
            return True
        else:
            logging.error(f'adding config failed; error: {response.content}')
            return False

    def get(self, url, params=None, format=None):
        logging.debug(f'getting url:{url} params:{params} format:{format}')
        if url and params and format:
            return self._checkmk.get(url=url,
                                     params=params,
                                     format=format)
        elif url and params:
            return self._checkmk.get(url=url,
                                     params=params)
        else:
            return self._checkmk.get(url=url)
