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

### For each run:

You need a new database - create one:

    docker run -it --rm --network bodsdatagettersnetwork postgres psql -h bodsdatagetters -U postgres -c "CREATE DATABASE run1"

Run command to init database:

    DATABASE=postgres://postgres:1234@localhost:54321/run1 python ukpsc.py init

Download data from http://download.companieshouse.gov.uk/en_pscdata.html

For each  file you get, run the load command:


    DATABASE=postgres://postgres:1234@localhost:54321/run1 python ukpsc.py loadpscfile psc-snapshot-2022-02-17_1of20.txt

Then add Open Corporates Info:

    DATABASE=postgres://postgres:1234@localhost:54321/run1 python ukpsc.py addopencorporates



## Cleaning up

    docker stop bodsdatagetters
    docker rm bodsdatagetters
    docker volume rm bodsdatagetterspostgresdata
    docker network rm bodsdatagettersnetwork

