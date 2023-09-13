import logging
import json
import requests
import pprint

class Rest(object):

    def __init__(self, sot, *named, **unnamed):
        logging.debug(f'initializing REST object')
        properties = self.__convert_arguments_to_properties(unnamed, named)
        self._sot = sot
        self._authentication = properties.get('authentication','bearer')
        self._username = properties.get('username')
        self._password = properties.get('password')
        self._api_url = properties.get('url')
        self._token = properties.get('token')
        self._session = None
        self._headers = None

        logging.debug(f'url: {self._api_url} token: {self._token} user: {self._username}')

    def __convert_arguments_to_properties(self, *unnamed, **named):
        """ converts unnamed (dict) and named arguments to a single property dict """
        properties = {}
        if len(unnamed) > 0:
            for param in unnamed:
                if isinstance(param, dict):
                    for key,value in param.items():
                        properties[key] = value
                elif isinstance(param, str):
                    # it is just a text like log('something to log')
                    return param
                elif isinstance(param, tuple):
                    for tup in param:
                        if isinstance(tup, dict):
                            for key,value in tup.items():
                                properties[key] = value
                        if isinstance(tup, str):
                            return tup
                elif isinstance(param, list):
                    return param
                else:
                    logging.error(f'cannot use paramater {param} / {type(param)} as value')
        for key,value in named.items():
                properties[key] = value
        
        return properties

    def session(self):
        logging.debug(f'starting session for {self._username} on {self._api_url}')
        if self._session is None:
            if self._authentication == 'bearer' and self._username is not None and self._password is not None:
                self._session = requests.Session()
                self._session.headers['Authorization'] = f"Bearer {self._username} {self._password}"
                self._session.headers['Accept'] = 'application/json'
            elif self._authentication == 'basic' and self._username is not None and self._password is not None:
                self._session = requests.Session()
                self._session.auth = (self._username, self._password)
                logging.debug(f'session basic auth user: {self._username} pass: {self._password}')
            elif self._token is not None:
                self._session = requests.Session()
                self._session.headers['Authorization'] = f"Token {self._token}"
                self._session.headers['Accept'] = 'application/json'
        else:
            logging.debug(f'active session detected; please close session before starting new one')

    def set_headers(self, *unnamed, **named):
        properties = self.__convert_arguments_to_properties(unnamed, named)
        if self._headers is None:
            self._headers = {}
        for key, value in properties.items():
            logging.debug(f'set header key: {key} value: {value}')
            self._headers[key] = value

    def get(self, *unnamed, **named):
        logging.debug(f'sending GET request to {self._api_url}')
        properties = self.__convert_arguments_to_properties(unnamed, named)

        # modify URL
        properties['url'] = "%s/%s" % (self._api_url, properties['url'])
        # check if format is present
        format = properties.get('format')
        if format is not None:
            del properties['format']
        # add headers to properties
        if self._headers is not None:
            properties['headers'] = self._headers
        resp = self._session.get(**properties)
        logging.debug(f'got status {resp.status_code}')
        if resp.status_code == 200:
            if format == "json":
                return resp.json()
            elif format == "content":
                return resp.content()
            else:
                return resp
        else:
            return resp

    def post(self, *unnamed, **named):
        logging.debug(f'sending POST request to {self._api_url}')
        properties = self.__convert_arguments_to_properties(unnamed, named)
        # modify URL
        properties['url'] = "%s/%s" % (self._api_url, properties['url'])

        # add default headers if no header was passed
        if self._headers and not 'headers' in properties:
            properties['headers'] = self._headers
        return self._session.post(**properties)

    def put(self, *unnamed, **named):
        logging.debug(f'sending PUT request to {self._api_url}')
        properties = self.__convert_arguments_to_properties(unnamed, named)

        # modify URL
        properties['url'] = "%s/%s" % (self._api_url, properties['url'])
        # add headers to properties
        if self._headers is not None:
            if 'headers' in properties:
                properties['headers'].update(self._headers)
            else:
                properties['headers'] = self._headers

        return self._session.put(**properties)

    def patch(self, *unnamed, **named):
        logging.debug(f'sending PATCH request to {self._api_url}')
        properties = self.__convert_arguments_to_properties(unnamed, named)

        # modify URL
        properties['url'] = "%s/%s" % (self._api_url, properties['url'])
        # add headers to properties
        if self._headers is not None:
            if 'headers' in properties:
                properties['headers'].update(self._headers)
            else:
                properties['headers'] = self._headers

        return self._session.patch(**properties)
