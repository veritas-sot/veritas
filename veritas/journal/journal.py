import logging
import os
import yaml
import psycopg2
from datetime import datetime, timezone
from ..tools import tools


class Journal(object):

    def __init__(self, uuid=None):
        self.__basedir = os.path.abspath(os.path.dirname(__file__))
        self.__uuid = uuid
        self.__conn = None
        self.__cursor = None

        # connect to database
        self._connect_to_db()

    def new(self, app=None):
        """create new journal entry"""
        logging.debug(f'creating new journal entry')

        sql = """INSERT INTO metadata(status)
             VALUES('active') RETURNING uuid;"""
        self.__cursor.execute(sql, ())

        # get the generated uuid back
        self.__uuid = self.__cursor.fetchone()[0]
        logging.debug(f'this journal entry has uuid {self.__uuid}')

        # commit the changes to the database
        self.__conn.commit()

        # return UUID back to user
        return self.__uuid

    def close(self):
        """close existing journal entry"""
        logging.debug(f'closing journal {self.__uuid}')

        sql = """UPDATE metadata SET status = %s WHERE uuid = %s"""
        response = self.__cursor.execute(sql, ('closed', self.__uuid))

        # Commit the changes to the database
        self.__conn.commit()
        # Close communication with the PostgreSQL database
        self.__cursor.close()

        return True

    def message(self, app=None, message=''):
        """write message to journal entry"""
        sql = """INSERT INTO entries(uuid, app, message)
             VALUES(%s, %s, %s) RETURNING id;"""
        self.__cursor.execute(sql, (self.__uuid, app, message))

        # get the generated id back
        id = self.__cursor.fetchone()[0]
        logging.debug(f'this journal entry has id {id}')

        # commit the changes to the database
        self.__conn.commit()

        # return UUID back to user
        return id


    # ---- internals ----

    def _connect_to_db(self):
        self.__conn = psycopg2.connect(
                database="journal",
                        host="127.0.0.1",
                        user="postgres",
                        password="postgres",
                        port="5432")

        self.__cursor = self.__conn.cursor()
