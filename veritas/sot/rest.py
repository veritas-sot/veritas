import json
import requests
import pprint
from ..tools import tools
from loguru import logger


class Rest(object):

    def __init__(self, sot, *named, **unnamed):
        properties = tools.convert_arguments_to_properties(unnamed, named)
        self._sot = sot
        self._authentication = properties.get('authentication','bearer')
        self._username = properties.get('username')
        self._password = properties.get('password')
        self._api_url = properties.get('url')
        self._token = properties.get('token')
        self._verify_ssl = properties.get('verify_ssl', True)
        self._session = None
        self._headers = None

        logger.debug(f'url: {self._api_url} token: {self._token} user: {self._username}')

    def session(self):
        logger.debug(f'starting session for {self._username} on {self._api_url}')
        if self._session is None:
            if self._authentication == 'bearer' and self._username is not None and self._password is not None:
                self._session = requests.Session()
                self._session.headers['Authorization'] = f"Bearer {self._username} {self._password}"
                self._session.headers['Accept'] = 'application/json'
            elif self._authentication == 'basic' and self._username is not None and self._password is not None:
                self._session = requests.Session()
                self._session.auth = (self._username, self._password)
                logger.debug(f'session basic auth user: {self._username} pass: {self._password}')
            elif self._token is not None:
                self._session = requests.Session()
                self._session.headers['Authorization'] = f"Token {self._token}"
                self._session.headers['Accept'] = 'application/json'
        else:
            logger.debug(f'active session detected; please close session before starting new one')

    def set_headers(self, *unnamed, **named):
        properties = tools.convert_arguments_to_properties(unnamed, named)
        if self._headers is None:
            self._headers = {}
        for key, value in properties.items():
            logger.debug(f'set header key: {key} value: {value}')
            self._headers[key] = value

    def get(self, *unnamed, **named):
        logger.debug(f'sending GET request to {self._api_url}')
        properties = tools.convert_arguments_to_properties(unnamed, named)

        # modify URL
        properties['url'] = "%s/%s" % (self._api_url, properties['url'])
        properties['verify'] = self._verify_ssl
        # check if format is present
        format = properties.get('format')
        if format is not None:
            del properties['format']
        # add headers to properties
        if self._headers is not None:
            properties['headers'] = self._headers
        resp = self._session.get(**properties)
        logger.debug(f'got status {resp.status_code}')
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
        logger.debug(f'sending POST request to {self._api_url}')
        properties = tools.convert_arguments_to_properties(unnamed, named)
        # modify URL
        properties['url'] = "%s/%s" % (self._api_url, properties['url'])
        properties['verify'] = self._verify_ssl

        # add default headers if no header was passed
        if self._headers and not 'headers' in properties:
            properties['headers'] = self._headers
        return self._session.post(**properties)

    def put(self, *unnamed, **named):
        logger.debug(f'sending PUT request to {self._api_url}')
        properties = tools.convert_arguments_to_properties(unnamed, named)

        # modify URL
        properties['url'] = "%s/%s" % (self._api_url, properties['url'])
        properties['verify'] = self._verify_ssl
        # add headers to properties
        if self._headers is not None:
            if 'headers' in properties:
                properties['headers'].update(self._headers)
            else:
                properties['headers'] = self._headers

        return self._session.put(**properties)

    def patch(self, *unnamed, **named):
        logger.debug(f'sending PATCH request to {self._api_url}')
        properties = tools.convert_arguments_to_properties(unnamed, named)

        # modify URL
        properties['url'] = "%s/%s" % (self._api_url, properties['url'])
        properties['verify'] = self._verify_ssl
        # add headers to properties
        if self._headers is not None:
            if 'headers' in properties:
                properties['headers'].update(self._headers)
            else:
                properties['headers'] = self._headers

        return self._session.patch(**properties)
