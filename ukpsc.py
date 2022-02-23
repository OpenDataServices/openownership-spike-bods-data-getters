from bodsdatagetters.ukpsc.run import UKPSCRun
import click
import os
import csv

@click.group()
def cli():
    pass


@click.command("init")
def init_command():
    click.echo("INIT")
    run = UKPSCRun(os.getenv("DATABASE"))
    run.init()


@click.command("loadpscdata")
@click.argument("apikey")
def loadpscdata_command(apikey: str, count: int = -1):
    click.echo("Loading data")
    run = UKPSCRun(os.getenv("DATABASE"))
    run.load_psc_data(apikey)


@click.command("addopencorporatescompanies")
@click.argument("filename")
def addopencorporates_companies_command(filename: str):
    click.echo("Adding Open Corporates Companies")
    run = UKPSCRun(os.getenv("DATABASE"))
    with open(filename) as csvfile:
        csvreader = csv.reader(csvfile)
        headers = next(csvreader)
        for row in csvreader:
            data = {headers[i]: row[i] for i in range(min(len(headers),len(row)))}
            run.process_open_corporates_companies(data)



@click.command("addopencorporatesofficers")
@click.argument("filename")
def addopencorporates_companies_officers(filename: str):
    click.echo("Adding Open Corporates Officers")
    run = UKPSCRun(os.getenv("DATABASE"))
    with open(filename) as csvfile:
        csvreader = csv.reader(csvfile)
        headers = next(csvreader)
        for row in csvreader:
            data = {headers[i]: row[i] for i in range(min(len(headers),len(row)))}
            run.process_open_corporates_officers(data)



@click.command("dumpbods")
@click.argument("filename")
def dumpbods_command(
     filename: str
):
    click.echo("Dump BODS")
    run = UKPSCRun(os.getenv("DATABASE"))
    with open(filename, "w") as fp:
        run.dump_bods(fp)


cli.add_command(init_command)
cli.add_command(loadpscdata_command)
cli.add_command(addopencorporates_companies_command)
cli.add_command(addopencorporates_companies_officers)
cli.add_command(dumpbods_command)

if __name__ == "__main__":
    cli()
