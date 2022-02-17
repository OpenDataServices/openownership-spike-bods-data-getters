import psycopg2



class UKPSCRun:


    def __init__(self, db_connection_string):
        self._conn = psycopg2.connect(db_connection_string)


    def init(self):
        cur = self._conn.cursor()
        cur.execute("CREATE TABLE person (id BIGSERIAL  PRIMARY KEY);")
        cur.execute("CREATE TABLE entity (id BIGSERIAL  PRIMARY KEY);")
        cur.execute("CREATE TABLE ownership_or_control (id BIGSERIAL  PRIMARY KEY);")
        self._conn.commit()
        cur.close()

