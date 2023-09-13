from copy import deepcopy
import logging
import yaml


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

def convert_arguments_to_properties(*unnamed, **named):
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
