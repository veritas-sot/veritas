import psycopg2
import zmq
from zmq.log.handlers import PUBHandler
from loguru import logger


class Messagebus():

    def __init__(self, 
                 app=None, uuid=None,
                 database=None,
                 zeromq=None):
        """init veritas messagesbus"""

        # general
        self.__app_name = app
        self.__uuid = uuid

        # database
        self._database = None
        self._db_connection = None
        self._cursor = None
        
        if database:
            self._database = database
            self._connect_to_db()

        # zeroMQ
        if zeromq:
            protocol = zeromq.get('protocol','tcp')
            host = zeromq.get('host','127.0.0.1')
            port = zeromq.get('port',12345)
            context = zmq.Context()
            socket = zmq.Context().socket(zmq.PUB)
            socket.connect(f'{protocol}://{host}:{port}')
            zmq_handler = PUBHandler(socket)
            logger.add(zmq_handler)

        # list of sinks
        self._sinks = []


    def write(self, message):
        record = message.record
        levelno = record['level'].no
        levelname = record['level'].name
        message = record['message']
        filename = record['file'].name
        pathname = record['file'].path
        lineno = record['line']
        module = record['module']
        function = record['function']
        processname = record['process'].name
        threadname = record['thread'].name
        exception = record['exception']

        if self._database:
            self._write_to_database(levelno, 
                                    levelname, 
                                    message, 
                                    filename, 
                                    pathname, 
                                    lineno, 
                                    module, 
                                    function, 
                                    processname, 
                                    threadname, 
                                    exception)

    # internals

    def _connect_to_db(self):
        """connet to database"""
        self._db_connection = psycopg2.connect(
                host=self._database['host'],
                database=self._database['database'],
                user=self._database['user'],
                password=self._database['password'],
                port=self._database['port'])

        self._cursor = self._db_connection.cursor()

    def _write_to_database(self, levelno, levelname, message, filename, 
                            pathname, lineno, module, function, 
                            processname, threadname, exception):
        if self.__uuid:
            sql = """INSERT INTO log(app, uuid, levelno, levelname, message, filename, pathname, lineno, module, function, processname, threadname, exception)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            self._cursor.execute(sql, (self.__app_name, 
                                       self.__uuid, 
                                       levelno, 
                                       levelname, 
                                       message,
                                       filename,
                                       pathname, 
                                       lineno, 
                                       module, 
                                       function, 
                                       processname,
                                       threadname,
                                       exception))
        else:
            sql = """INSERT INTO log(app, levelno, levelname, message, filename, pathname, lineno, module, function, processname, threadname, exception)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING uuid;"""
            self._cursor.execute(sql, (self.__app_name, 
                                       levelno, 
                                       levelname, 
                                       message,
                                       filename,
                                       pathname, 
                                       lineno, 
                                       module, 
                                       function, 
                                       processname,
                                       threadname,
                                       exception))

            # get the generated uuid back
            if not self.__uuid:
                self.__uuid = self._cursor.fetchone()[0]

        # commit the changes to the database
        self._db_connection.commit()


    