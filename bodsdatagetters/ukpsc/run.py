import psycopg2
import psycopg2.extras
import json
import requests
import base64

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

    def load_psc_data(self, apikey: str):
        headers = {'Authorization': 'Basic ' + base64.b64encode(apikey.encode('ascii')).decode("ascii") }
        # TODO What value should timepoint be to start at the start of the data stream?
        # Passing no timepoint gets you events published now.
        # But passing timepoint=1 gets you a 416 header response.
        # Presumably there is a magic number that you need to pass that gets you from the start of the data, but doesn't 416.
        # Docs say to pass an integer but not what scheme is.
        # Real data has "2022-02-23T11:41:28" == 2749113 and that is no integer time encoding scheme I know off, so I can't guess.
        timepoint = 2749100
        r = requests.get(
            'https://stream.companieshouse.gov.uk/persons-with-significant-control?timepoint='+str(timepoint),
            headers=headers,
            stream=True
        )
        if r.status_code != 200:
            print(r.text)
            raise Exception("NON 200 ERROR! " + str(r.status_code))
        for line in r.iter_lines():
            # TODO Encoding errors have been seen when loading data - this needs to be looked into
            data = json.loads(line.decode("utf-8"))
            print(data)
            self.add_line_from_streaming_psc_data(data)

    def add_line_from_streaming_psc_data(self, data: dict):

        resource_uri_bits = data.get('resource_uri').split('/')
        company_number = resource_uri_bits[2]

        # TODO One transaction per line is going to be slow, be much faster if we could batch in groups
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO  entity (company_number) VALUES (%s) ON CONFLICT DO NOTHING",
            (company_number,)
        )
        cur.execute(
            "INSERT INTO psc_data (company_number, psc_data) VALUES (%s, %s)",
            (company_number, json.dumps(data))
        )
        self._conn.commit()
        cur.close()

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
        # TODO later there may be a better field than id to sort by, like a date field
        cur.execute(
            "SELECT * FROM psc_data ORDER BY id ASC"
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
                    "id": "https://opencorporates.com/companies/gb/" + record['company_number']
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
        if record['open_corporates_data']:
            entity_statement['name'] = record['open_corporates_data']['name']

        return entity_statement

    def _get_person_statement_for_psc_data_row(self, record):
        # TODO is there a form of PSC where another company has control? )
        # TODO From the data model spec, it's not clear what order these address fields should be in to make a sensible address
        address_bits = [
            record['psc_data']['data']['address'].get('po_box'),
            record['psc_data']['data']['address'].get('care_of'),
            record['psc_data']['data']['address'].get('premises'),
            record['psc_data']['data']['address'].get('address_line_1'),
            record['psc_data']['data']['address'].get('address_line_2'),
            record['psc_data']['data']['address'].get('locality'),
            record['psc_data']['data']['address'].get('region'),
            record['psc_data']['data']['address'].get('postal_code'),
            record['psc_data']['data']['address'].get('country'),
        ]
        address_string = ",".join([i for i in address_bits if i])
        person_statement = {
            "statementID": "person" + str(record['id']),  # TODO this is a shitty id to use as it will change every time
            "statementType": "personStatement",
            "personType": "knownPerson",
            "isComponent": False,  # TODO ???????????????????????????????????
            "names": [
                {
                    "type": "individual",
                    "fullName": record['psc_data']['data']['name']
                }
            ],
            "addresses": [
                {
                    "type": "registered",
                    "address": address_string,
                    "postCode": record['psc_data']['data']['address'].get('postal_code'),
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
            },
            "interests":[]
        }
        for nature_of_control in record['psc_data']['data']['natures_of_control']:
            # See https://github.com/companieshouse/api-enumerations/blob/master/psc_descriptions.yml for complete list
            # TODO add rest from above list
            if nature_of_control == 'ownership-of-shares-25-to-50-percent':
                ownership_or_control_statement['interests'].append({
                    'type':'shareholding',
                    'share': {
                        'minimum': 25,
                        'maximum': 50
                    }
                })
            elif nature_of_control == 'ownership-of-shares-50-to-75-percent':
                ownership_or_control_statement['interests'].append({
                    'type':'shareholding',
                    'share': {
                        'minimum': 50,
                        'maximum': 74
                    }
                })
            elif nature_of_control == 'ownership-of-shares-75-to-100-percent':
                ownership_or_control_statement['interests'].append({
                    'type':'shareholding',
                    'share': {
                        'minimum': 75,
                        'maximum': 100
                    }
                })
            elif nature_of_control == 'voting-rights-25-to-50-percent':
                ownership_or_control_statement['interests'].append({
                    'type':'voting-rights',
                    'share': {
                        'minimum': 25,
                        'maximum': 50
                    }
                })
            elif nature_of_control == 'voting-rights-50-to-75-percent':
                ownership_or_control_statement['interests'].append({
                    'type':'voting-rights',
                    'share': {
                        'minimum': 50,
                        'maximum': 74
                    }
                })
            elif nature_of_control == 'voting-rights-75-to-100-percent':
                ownership_or_control_statement['interests'].append({
                    'type':'voting-rights',
                    'share': {
                        'minimum': 75,
                        'maximum': 100
                    }
                })
            elif nature_of_control == 'significant-influence-or-control':
                ownership_or_control_statement['interests'].append({
                    'type':'other-influence-or-control'
                })
        return ownership_or_control_statement