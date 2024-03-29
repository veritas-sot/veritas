from loguru import logger


class Plugin(object):
    """This class is a singleton that holds the registry of plugins.

    Returns
    -------
    Plugin
        The plugin object
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            logger.debug('Creating plugin object')
            cls._instance = super(Plugin, cls).__new__(cls)
            cls._registry = {'kobold': {},
                             'jobschleuder': {},
                             'configmanagement': {},
                             'plugins': {}}
        return cls._instance

    def get(self, app:str, name:str) -> callable:
        """return registry entry

        Parameters
        ----------
        app : str
            name of the app
        name : str
            name of the registered plugin

        Returns
        -------
        method
           the method that is registered
        """
        return self._registry.get(app,{}).get(name)

    def get_kobold_plugin(self, name:str) -> callable:
        """return kobold plugin

        Parameters
        ----------
        name : str
            name of the registered plugin

        Returns
        -------
        callable
            the method that is registered
        """
        return self._registry.get('kobold',{}).get(name)
    
    def get_jobschleuder_plugin(self, name:str) -> callable:
        """return jobschleuder plugin

        Parameters
        ----------
        name : str
            name of the registered plugin

        Returns
        -------
        callable
            the method that is registered
        """
        return self._registry.get('jobschleuder',{}).get(name)

    def get_configmanagement_plugin(self, name:str) -> callable:
        """return configmanagement plugin

        Parameters
        ----------
        name : str
            name of the registered plugin

        Returns
        -------
        callable
            the method that is registered
        """
        return self._registry.get('configmanagement',{}).get(name)
    
    def get_registry(self, app:str) -> dict:
        """return registry

        Parameters
        ----------
        app : str
            name of the app

        Returns
        -------
        dict
            the registry of the app
        """
        return self._registry.get(app)

    # internals

    def add(self, app:str, name:str, method:callable) -> None:
        """register a plugin

        Parameters
        ----------
        app : str
            name of the app
        name : str
            name of the plugin
        method : callable
            the method to be registered
        """
        logger.debug(f'added {app}/{name} to registry')
        self._registry[app][name] = method

def kobold(name:str):
    """decorator to register a kobold plugin

    Parameters
    ----------
    name : str
        name to be registered
    """    
    def decorator(func):
        plugin = Plugin()
        logger.debug(f'registering {name} / {func}')
        plugin.add('kobold', name, func)
        # return fn unmodified
        return func
    return decorator

def jobschleuder(name:str):
    """decorator to register a jobschleuder plugin

    Parameters
    ----------
    name : str
        name to be registered
    """    
    def decorator(func):
        plugin = Plugin()
        logger.debug(f'registering {name} / {func}')
        plugin.add('jobschleuder', name, func)
        # return fn unmodified
        return func
    return decorator

def configmanagement(name:str):
    """register configmanagement plugin

    Parameters
    ----------
    name : str
        name to be registered
    """    
    def decorator(func):
        plugin = Plugin()
        logger.debug(f'registering {name} / {func}')
        plugin.add('configmanagement', name, func)
        # return fn unmodified
        return func
    return decorator

def register(name:str):
    """register arbitary plugin

    Parameters
    ----------
    name : str
        name to be registered
    """    
    def decorator(func):
        plugin = Plugin()
        logger.debug(f'registering {name} / {func}')
        plugin.add('plugins', name, func)
        # return fn unmodified
        return func
    return decorator
