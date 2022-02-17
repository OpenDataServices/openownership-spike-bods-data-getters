import psycopg2
import json


class UKPSCRun:


    def __init__(self, db_connection_string):
        self._conn = psycopg2.connect(db_connection_string)


    def init(self):
        cur = self._conn.cursor()
        cur.execute(
            "CREATE TABLE entity ("+
            "company_number VARCHAR(200)  PRIMARY KEY"+
            ");"
        )
        cur.execute(
            "CREATE TABLE psc_data ("+
            "id BIGSERIAL PRIMARY KEY, "+
            "company_number VARCHAR(200), "+
            "psc_data JSONB "+
            ");"
        )
        self._conn.commit()
        cur.close()

    def add_data_line(self, line):
        json_data = json.loads(line)
        print(json.dumps(json_data, indent=2))
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO  entity (company_number) VALUES (%s) ON CONFLICT DO NOTHING",
            (json_data['company_number'],)
        )
        cur.execute(
            "INSERT INTO  psc_data (company_number, psc_data) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (json_data['company_number'], json.dumps(json_data['data']))
        )
        self._conn.commit()
        cur.close()
