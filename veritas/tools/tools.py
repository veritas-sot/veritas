import logging
import colorlog
import yaml
import os
import getpass
import pytricia
import hashlib
from openpyxl import load_workbook


def get_value_from_dict(dictionary, keys):
    if dictionary is None:
        return None

    nested_dict = dictionary

    for key in keys:
        try:
            nested_dict = nested_dict[key]
        except KeyError as e:
            return None
        except IndexError as e:
            return None
        except TypeError as e:
            return nested_dict

    return nested_dict

def get_loglevel(level):
    if level == 'debug':
        return logging.DEBUG
    elif level == 'info':
        return logging.INFO
    elif level == 'critical':
        return logging.CRITICAL
    elif level == 'error':
        return logging.ERROR
    else:
        return logging.NOTSET

def set_loglevel(args, config):
    loglevel = get_loglevel(args.loglevel) if args.loglevel else \
        get_loglevel(get_value_from_dict(config, ['general', 'logging', 'level']))
    
    log_format = get_value_from_dict(config, ['general', 'logging', 'format'])
    log_format = '%(asctime)s %(levelname)s:%(message)s' if not log_format else log_format
    logging.basicConfig(level=loglevel, format=log_format)

def convert_arguments_to_properties(*unnamed, **named):
    """ convert unnamed (dict) and named arguments to a single property dict """
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
                    elif isinstance(tup, str):
                        return tup
                    elif isinstance(tup, list):
                        return tup
            elif isinstance(param, list):
                return param
            else:
                logging.error(f'cannot use paramater {param} / {type(param)} as value')
    for key,value in named.items():
            properties[key] = value
    
    return properties

def get_username_and_password(args, sot, config):
    username = None
    password = None

    if args.profile is not None:
        username = config.get('profiles',{}).get(args.profile,{}).get('username')
        token = config.get('profiles',{}).get(args.profile,{}).get('password')
        if username and token:
            auth = sot.auth(encryption_key=os.getenv('ENCRYPTIONKEY'), 
                            salt=os.getenv('SALT'), 
                            iterations=int(os.getenv('ITERATIONS')))
            password = auth.decrypt(token)

    # overwrite username and password if configured by user
    username = args.username if args.username else username
    password = args.password if args.password else password

    username = input("Username (%s): " % getpass.getuser()) if not username else username
    password = getpass.getpass(prompt="Enter password for %s: " % username) if not password else password

    return username, password

def read_excel_file(filename):

    response = {}
    table = []

    # Load the workbook
    workbook = load_workbook(filename = filename)

    # Select the active worksheet
    worksheet = workbook.active
    
    # loop through table and build list of dict
    rows = worksheet.max_row
    columns = worksheet.max_column + 1 
    for row in range(2, rows + 1):
        line = {}
        for col in range(1, columns):
            key = worksheet.cell(row=1, column=col).value
            value = worksheet.cell(row=row, column=col).value
            line[key] = value
        table.append(line)

    return table

def set_value(mydict, paths, value):
    # write value to nested dict
    # we split the path by using '__'
    parts = paths.split('__')
    for part in parts[0:-1]:
        # add {} if item does not exists
        # this loop create an empty path
        mydict = mydict.setdefault(part, {})
    # at last write value to dict
    mydict[parts[-1]] = value

def get_prefix_path(prefixe, ip):
    """return prefix path"""
    prefix_path = []
    pyt = pytricia.PyTricia()

    # build pytricia tree
    for prefix_ip in prefixe:
        pyt.insert(prefix_ip, prefix_ip)

    try:
        prefix = pyt.get(ip)
    except Exception as exc:
        logging.error(f'prefix not found; using 0.0.0.0/0')
        prefix = "0.0.0.0/0"
    prefix_path.append(prefix)

    parent = pyt.parent(prefix)
    while (parent):
        prefix_path.append(parent)
        parent = pyt.parent(parent)
    return prefix_path[::-1]

def calculate_md5(row):
    data = ""
    for d in row:
        if isinstance(d, list):
            my_list = ''.join(d)
            data += my_list
        elif d is None or d == 'null':
            pass
        else:
            data += d
    return hashlib.md5(data.encode('utf-8')).hexdigest()

def flatten_json(y):
    """flatten json"""
    # source https://towardsdatascience.com/flattening-json-objects-in-python-f5343c794b10
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(y)
    return out
