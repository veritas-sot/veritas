import logging
import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class Auth(object):

    def __init__(self, sot, **named):
        logging.debug(f'Creating AUTH object;')
        self._encryption_key_ascii = None
        self._salt_bytes = None
        self._sot = sot
        if 'encryption_key' in named:
            self._encryption_key_ascii = named['encryption_key']
        if 'salt' in named:
            self._salt_bytes = str.encode(named['salt'])
        if 'iterations' in named and named['iterations'] is not None:
            self._iterations = named['iterations']
        else:
            self._iterations = 400000
        #logging.debug(f'salt: {self._salt_bytes} encryption_key: {self._encryption_key_ascii} iterations: {self._iterations}')

    def set_salt(self, salt):
        self._salt_bytes = str.encode(salt)

    def set__encryption_key(self, _encryption_key):
        self._encryption_key_ascii = _encryption_key

    def set_iterations(self, iterations):
        self._iterations = iterations

    def encrypt(self, password):
        password_bytes = str.encode(password)
        encrypt_pwd_bytes = str.encode(self._encryption_key_ascii)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt_bytes,
            iterations=self._iterations,
        )
        key = base64.urlsafe_b64encode(kdf.derive(encrypt_pwd_bytes))
        f = Fernet(key)
        token = f.encrypt(password_bytes)
        return base64.b64encode(token)

    def decrypt(self, token_ascii):
        token_bytes = base64.b64decode(token_ascii)
        encryption_key_bytes = str.encode(self._encryption_key_ascii)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt_bytes,
            iterations=self._iterations,
        )
        key = base64.urlsafe_b64encode(kdf.derive(encryption_key_bytes))

        f = Fernet(key)
        try:
            return f.decrypt(token_bytes).decode("utf-8")
        except Exception as e:
            logging.error("Wrong encryption key or salt %s" % e)
            return None
