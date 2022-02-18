from bodsdatagetters.ukpsc.run import UKPSCRun
import click
import os


@click.group()
def cli():
    pass


@click.command("init")
def init_command():
    click.echo("INIT")
    run = UKPSCRun(os.getenv("DATABASE"))
    run.init()


@click.command("loadpscfile")
@click.argument("filename")
def loadpscfile_command(filename: str):
    click.echo("Loading file")
    run = UKPSCRun(os.getenv("DATABASE"))
    with open(filename) as fp:
        for index, line in enumerate(fp):
            run.add_data_line(line.strip())


@click.command("addopencorporates")
def addopencorporates_command():
    click.echo("Adding Open Corporates")
    run = UKPSCRun(os.getenv("DATABASE"))
    run.add_open_corporates()



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
cli.add_command(loadpscfile_command)
cli.add_command(addopencorporates_command)
cli.add_command(dumpbods_command)

if __name__ == "__main__":
    cli()
