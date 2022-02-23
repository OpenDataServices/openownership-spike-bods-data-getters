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

## Architecture

This is designed to be used in a "run once" mode to provide a one time process that we can be rerun regularly. 

This uses a Postgres database to store PSC and Open Corporates data that has been imported, 
and then maybe to store some state as BODS data is output.

(This was done before we switched to the streaming PSC API - when we were taking 2 bulk data imports as input this made sense.
Now that we are using the streaming PSC API it would maybe be better to have a pipeline model, or a model where the database is kept between runs to reduce the amount of work needed.)

The process is in order:

1. Load all PSC statements into database
2. Process bulk Open Corporates information. For all information that may be relevant, save in database.
3. Extract BODS statements by looping through all PSC statements in order and outputting required BODS statements.

Open Corporates information that may be relevant includes: 
* most of the "GB" country information
* entities in foreign countries when they are listed in the PSC data
Note it is not ALL Open Corporates data - so the order is done carefully so that only needed information is loaded into the database to save space.

(This is also done so that the loading into the database operation can be done once, then the bods output stage could be run multiple times with tweaks. 
When we were using the Open Corporates REST API and were making one call per bit of info that was more important. Now we use bulk Open Corporates info this is less important.)


## Still to do

See TODO comments in source code for minor points.

### Deduping people

The same person can appear in the PSC data with no independent identifier to dedupe them.

This means multiple people statements may be issued for the same people.

Solutions:

The `resource_uri` field in PSC data may provide a way to dedupe people in the same company at least.

Linking to the Open Corporates data may provide a UID that can dedupe people across companies. It is for this purpose Open Corporates Officer data is loaded. When given any PSC statement, it may be possible to look up all `open_corporates_officer` table entries for that company number and match a name. However, that name matching may be fragile.

### Dates & statements over time

The major point that needs to be done is work out the dates and replacements of statements to ensure the historical data model of BODS. 

What dates should be on published BODS statements?

What happens when a person's interest changes over time - are multiple PSC statements published and do 

There is a problem which I think is unavoidable; we only have available to us the latest information on an entity. If an entity changes over time (eg changes name) then we should be publishing several BODS statements. But the BODS standard requires us to publish an entity statement before we publish a PSC/Ownership-and-control statement. If the first PSC statement is from 2019 then we have to publish an entity statement dated 2019 with the latest company information from 2022.

Note some dates data in the PSC data seems ... unhelpful. Real data has been seen with ` "notified_on":"2021-06-01"` but  `"published_at":"2022-02-23T11:41:28"` and I don't understand why these are significantly different.

It was impossible to really look into this without getting most of the PSC data to analyse and I didn't have the time to do that.


### Id's of statements

It would be ideal to have stable ID's so that a bulk processing done one month then another processing the next month had the same ID's on BODS Statements.

The PSC data has some fields (`resource_id` & `resource_uri`) that may be useful here, but we need to check if these are stable. 

### When entities declare an interest in another entity

This is marked by `"kind": "corporate-entity-person-with-significant-control"` in the PSC data.

In this case, the `identification` block is meant to be populated with information. Ideally we could mark this as another company we care about by storing that in the entities table. This would mean it is enriched with Open Corporates data and an entity statement is output for it.

However, it is clear there is no data validation on  the `identification` block. In our very limited sample of real data, we saw still values of:

* `"legal_form": "Private Company Limited By Shares", "legal_authority": "Companies Act 2006", "place_registered": "Uk Register Of Companies", "country_registered": "United Kingdom"`
* `"legal_form": "Limited By Shares- Corporate", "legal_authority": "Uk", "place_registered": "England", "country_registered": "England"`
* `"legal_form": "Limited Company", "legal_authority": "Companies Act", "place_registered": "England & Wales", "country_registered": "England And Wales"`

We need to load lots of data and do a data cleaning exercise before continuing with this.
