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
            "CREATE TABLE open_corporates_officer ("+
            "id BIGSERIAL PRIMARY KEY, "+
            "company_number VARCHAR(200),"+
            "open_corporates_data JSONB NULL "
            ");"
        )
        cur.execute("CREATE INDEX open_corporates_officer_company_number ON open_corporates_officer (company_number);")
        cur.execute(
            "CREATE TABLE psc_data ("+
            "id BIGSERIAL PRIMARY KEY, "+
            "company_number VARCHAR(200), "+
            "psc_data JSONB "+
            ");"
        )
        cur.execute("CREATE INDEX psc_data_company_number ON psc_data (company_number);")
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
        #raise Exception("JUST ONE")

    def process_open_corporates_companies(self, data):
        # GB companies only
        if data['jurisdiction_code'] != 'gb':
            return

        # Update
        # This also means we are checking the data exists in PSC data.
        cur = self._conn.cursor()
        cur.execute(
            "UPDATE entity SET open_corporates_data=%s WHERE company_number=%s",
            (json.dumps(data), data['company_number'])
        )
        self._conn.commit()
        cur.close()

    def process_open_corporates_officers(self, data):
        # GB companies only
        if data['jurisdiction_code'] != 'gb':
            return

        # Work
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT COUNT(*) AS c FROM entity WHERE company_number=%s",
            (data['company_number'],)
        )
        count_data = cur.fetchone()
        if count_data['c'] > 0:
            cur.execute(
                "INSERT INTO  open_corporates_officer (company_number, open_corporates_data) VALUES (%s, %s)",
                (data['company_number'], json.dumps(data))
            )
            self._conn.commit()
        cur.close()


    def dump_bods(self, output_steam):
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT * FROM entity"
        )
        for record in cur:
            json.dump(self._get_entity_statement_for_entity_record(record), output_steam)
            output_steam.write("\n")
        cur.execute(
            "SELECT * FROM psc_data"
        )
        for record in cur:
            json.dump(self._get_person_statement_for_psc_data_row(record), output_steam)
            output_steam.write("\n")
            json.dump(self._get_ownership_or_control_statement_for_psc_data_row(record), output_steam)
            output_steam.write("\n")
        cur.close()

    def _get_entity_statement_for_entity_record(self, record):
        entity_statement = {
            "statementID": "entity" + record['company_number'],
            "statementType": "entityStatement",
            "entityType": "registeredEntity",
            "isComponent": False,  # TODO ???????????????????????????????????
            "name": record['open_corporates_data']['results']['company']['name'],
            "incorporatedInJurisdiction": {
                "name": "GB-Name",
                "code": "GB"
            },
            "identifiers": [
                {
                    "scheme": "GB-COH",
                    "id": record['company_number'],
                },
                {
                    "scheme": "OPENCORPORATESURL", # TODO not a valid scheme
                    "id": record['open_corporates_data']['results']['company']['opencorporates_url']
                }
            ],
            "publicationDetails": {
                "publicationDate": "",  # TODO ???????????????????????????????????
                "bodsVersion": "0.2",
                "publisher": {
                    "name": "SPIKE CONVERSION TOOL of UK PSR with additional Open Corporates Info"
                }
            }
        }
        return entity_statement

    def _get_person_statement_for_psc_data_row(self, record):
        # TODO is there a form of PSC where another company has control? )
        address_string = ",".join([i for i in [record['psc_data']['address']['premises'],
                                               record['psc_data']['address']['address_line_1'],
                                               record['psc_data']['address']['locality'],
                                               record['psc_data']['address']['postal_code'],
                                               record['psc_data']['address']['country'], ] if i])
        person_statement = {
            "statementID": "person" + str(record['id']),  # TODO this is a shitty id to use as it will change every time
            "statementType": "personStatement",
            "personType": "knownPerson",
            "isComponent": False,  # TODO ???????????????????????????????????
            "names": [
                {
                    "type": "individual",
                    "fullName": record['psc_data']['name']
                }
            ],
            "addresses": [
                {
                    "type": "registered",
                    "address": address_string,
                    "postCode": record['psc_data']['address']['postal_code'],
                    "country": ""  # TODO Can't assume GB, need to look at country ???????????????????????????????????
                }
            ],
            "publicationDetails": {
                "publicationDate": "",  # TODO ???????????????????????????????????
                "bodsVersion": "0.2",
                "publisher": {
                    "name": "SPIKE CONVERSION TOOL of UK PSR with additional Open Corporates Info"
                }
            }
        }
        return person_statement

    def _get_ownership_or_control_statement_for_psc_data_row(self, record):
        ownership_or_control_statement = {
            "statementID": "forperson" + str(record['id']),
            # TODO this is a shitty id to use as it will change every time
            "statementType": "ownershipOrControlStatement",
            "isComponent": False,  # TODO ???????????????????????????????????,
            "subject": {
                "describedByEntityStatement": "entity" + record['company_number'],
            },
            "interestedParty": {
                "describedByPersonStatement": "person" + str(record['id']),
            },
            "publicationDetails": {
                "publicationDate": "",  # TODO ???????????????????????????????????
                "bodsVersion": "0.2",
                "publisher": {
                    "name": "SPIKE CONVERSION TOOL of UK PSR with additional Open Corporates Info"
                }
            }
        }
        return ownership_or_control_statement