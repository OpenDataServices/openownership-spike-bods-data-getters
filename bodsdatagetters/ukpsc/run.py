import psycopg2
import psycopg2.extras
import json
import requests


class UKPSCRun:


    def __init__(self, db_connection_string):
        self._conn = psycopg2.connect(db_connection_string)


    def init(self):
        cur = self._conn.cursor()
        cur.execute(
            "CREATE TABLE entity ("+
            "company_number VARCHAR(200)  PRIMARY KEY,"+
            "open_corporates_data JSONB NULL "
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

    def add_open_corporates(self):
        cur = self._conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT company_number FROM entity WHERE open_corporates_data IS NULL "
        )
        for record in cur:
            self.add_open_corporates_to_entity(record['company_number'])
        cur.close()

    def add_open_corporates_to_entity(self, company_number: str):
        print(company_number)
        r = requests.get( 'https://api.opencorporates.com/companies/gb/' + company_number)
        if r.status_code != 200:
            raise Exception("NON 200 ERROR!")
        cur = self._conn.cursor()
        cur.execute(
            "UPDATE  entity SET open_corporates_data=%s WHERE company_number=%s ",
            (r.text, company_number)
        )
        self._conn.commit()
        cur.close()
        #raise Exception("JUST ONE")
