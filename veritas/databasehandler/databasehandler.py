import logging
import psycopg2



class DatabaseHandler(logging.Handler):

    def __init__(self, host, database, user, password, port=5432) -> None:
        logging.Handler.__init__(self=self)
        self.__cursor = None
        # database parameter
        self._database = database
        self._host = host
        self._user = user
        self._password = password
        self._port = port

        # connect to database
        self._connect_to_db()

    def _connect_to_db(self):
        self.__conn = psycopg2.connect(
                database=self._database,
                host=self._host,
                user=self._user,
                password=self._password,
                port=self._port)

        self.__cursor = self.__conn.cursor()

    def emit(self, record) -> None:
        # if we are using colorlog we have to "set" log_color and reset
        record.log_color = ""
        record.reset = ""
        formatted_msg = self.format(record)
        msg = record.getMessage()
        levelno = record.levelno
        levelname = record.levelname
        name = record.name
        pathname = record.pathname
        lineno = record.lineno
        func = record.funcName
        module = record.module
        processname = record.processName

        sql = """INSERT INTO log(levelno, levelname, message, pathname, name, lineno, func, module, processname, formatted_msg)
             VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;"""
        self.__cursor.execute(sql, (levelno, levelname, msg, pathname, name, lineno, func, module, processname, formatted_msg))

        # commit the changes to the database
        self.__conn.commit()
