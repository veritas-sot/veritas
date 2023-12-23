import logging
import queue
import structlog
from veritas.logging import databasehandler
from veritas.tools import tools
from logging.handlers import SysLogHandler, QueueHandler, QueueListener


def get_logger_from_config(config, loglevel):
    if loglevel:
        lglevel = tools.get_loglevel(loglevel)
    else:
        lglevel = tools.get_loglevel(config.get('general',{}).get('logging',{}).get('loglevel', 'info'))
    if config.get('general',{}).get('logging',{}).get('config'):
        logging_config_file = "%s/%s" % (BASEDIR, config.get('general',{}).get('logging',{}).get('config'))
    else:
        logging_config_file = None
    loghandler = config.get('general',{}).get('logging',{}).get('handler', 'stdout')
    use_color = config.get('general',{}).get('logging',{}).get('color', False)
    return _create_logger_environment(
        configfile=logging_config_file,
        logger='veritas',
        handler=loghandler,
        loglevel=lglevel)

def enable_database_logging(config, logger, app=None, uuid=None):
    database = config.get('general',{}).get('logging',{}).get('database')
    if database:
        logformat = config.get('general',{}) \
                          .get('logging',{}) \
                          .get('format', "%(levelname)s - %(message)s")
        return _add_queue_listener(logger=logger, 
                                   database=database, 
                                   app=app,
                                   uuid=uuid,
                                   format=logformat)
    else:
        logger.error(f'logging to database enabled but no database configured')
        return None

# internals

def _create_logger_environment(*unnamed, **named):
    """create veritas logger environment"""
    properties = tools.convert_arguments_to_properties(unnamed, named)
    
    logname = properties.get('logger', 'veritas')
    configfile = properties.get('configfile')
    loglevel = properties.get('loglevel', logging.INFO)
    address = properties.get('address','/dev/log')
    filename = properties.get('filename','veritas.log')
    disable_existing_loggers = properties.get('disable_existing_loggers', True)

    if configfile and not use_color:
        logging.config.fileConfig(configfile,
                                  disable_existing_loggers=disable_existing_loggers)
        return logging.getLogger('veritas')

    logger = logging.getLogger(logname)
    logger.setLevel(loglevel)

    if "syslog" == properties.get('handler'):
        handler = SysLogHandler(
            facility=SysLogHandler.LOG_DAEMON,
            address=address
        )
    elif "file" == properties.get('handler'):
        handler = logging.FileHandler(filename)
    elif "null" == properties.get('handler'):
        handler = logging.NullHandler()
    else:
        handler = logging.StreamHandler()
    
    structlog.configure(
        processors=[
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.CallsiteParameterAdder([
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO]
            ),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=True),
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer()
        ],
    )

    logger.addHandler(handler)
    handler.setFormatter(formatter)
    return logger

def _add_queue_listener(logger, database, app=None, uuid=None, format='%(levelname)s - %(message)s'):
    """add queue listener to logging"""
    log_queue = queue.Queue(-1)
    queue_handler = QueueHandler(log_queue)
    logger.addHandler(queue_handler)
    db_handler = databasehandler.DatabaseHandler(
        database=database['database'],
        host=database['host'],
        user=database['user'],
        password=database['password'],
        port=database.get('port, 5432'),
        app=app,
        uuid=uuid
    )

    formatter = logging.Formatter(
            fmt=format,
            datefmt="%Y-%m-%d %H:%M:%S"
    )
    db_handler.setFormatter(formatter)

    listener = QueueListener(log_queue, db_handler)
    return listener    
