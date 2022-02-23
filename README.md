# openownership-spike-bods-data-getters

## Running locally

Set up a Python Virtual Env

Install python deps

    pip install -r requirements.in 

Run a postgres server via Docker (or elsewhere):

    docker network create bodsdatagettersnetwork

    docker run -d \
    --name bodsdatagetters \
    -e POSTGRES_PASSWORD=1234 \
    -e PGDATA=/var/lib/postgresql/data/pgdata \
    -v bodsdatagetterspostgresdata:/var/lib/postgresql/data \
    --network bodsdatagettersnetwork  \
    -p 54321:5432 \
    postgres:14


## Getting UK PSC Streaming API Key

https://developer-specs.company-information.service.gov.uk/streaming-api/guides/authentication has links to:

* register for an account
* Go to https://developer.company-information.service.gov.uk/manage-applications and make an app
* Create a Streaming API key for your app (this step is different from making an app - the docs above are slightly out of date)

## Getting Open Corporates Bulk Data Files

Ask our OO contacts

### For each run:

You need a new database - create one:

    docker run -it --rm --network bodsdatagettersnetwork postgres psql -h bodsdatagetters -U postgres -c "CREATE DATABASE run1"

Run command to init database:

    DATABASE=postgres://postgres:1234@localhost:54321/run1 python ukpsc.py init

Get PSC Data:

    DATABASE=postgres://postgres:1234@localhost:54321/run1 python ukpsc.py loadpscdata APIKEY


This will keep running, you'll need to Ctrl-C manually

Then add Open Corporates Info - get bulk data as CSV files:

    DATABASE=postgres://postgres:1234@localhost:54321/run1 python ukpsc.py addopencorporatescompanies companies.csv
    DATABASE=postgres://postgres:1234@localhost:54321/run1 python ukpsc.py addopencorporatesofficers officers.csv

Finally dump your new BODS data to a file:

    DATABASE=postgres://postgres:1234@localhost:54321/run1 python ukpsc.py dumpbods bodsoutput.json

## Cleaning up

    docker stop bodsdatagetters
    docker rm bodsdatagetters
    docker volume rm bodsdatagetterspostgresdata
    docker network rm bodsdatagettersnetwork

