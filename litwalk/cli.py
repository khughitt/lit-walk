"""
lit-walk CLI
"""
import json
import os
import re
import sys
import datetime
import logging
import click
from typing import Any
from litwalk.walk import LitWalk
from rich import print
from rich.padding import Padding
from rich.table import Table
from rich.console import Console

# default config file location
if os.getenv('XDG_CONFIG_HOME'):
    conf_dir = os.path.join(str(os.getenv("XDG_CONFIG_HOME")), "lit-walk")
elif os.getenv('HOME'):
    conf_dir = os.path.join(str(os.getenv("HOME")), ".lit-walk")
else:
    raise Exception("Unable to infer location of config file automatically")
    sys.exit()

default_conf = os.path.join(conf_dir, "config.yml")

# initialize rich console
console = Console()

# initialize logger
logging.basicConfig(stream=sys.stdout, format='[%(levelname)s] %(message)s')
logger = logging.getLogger('lit-walk')

# print header
print("[cyan]========================================[/cyan]")
print(":books:", "[bold orchid]lit-walk[/bold orchid]")
print("[cyan]========================================[/cyan]")

@click.group()
@click.option("--config", default=default_conf, help="Path to lit-walk config file to use")
@click.option("--verbose", is_flag=True, help="If enabled, prints verbose output")
@click.pass_context
def cli(ctx, config:str, verbose:bool):
    """Initialize CLI"""
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARN)

    logger.info("Initializing lit-walk...")

    # initialize lit
    ctx.obj = LitWalk(config, verbose)

@cli.command
@click.argument("target", type=str)
@click.option("--skip-check", help="If enabled, skips check for existing articles", default=False)
@click.pass_obj
def add(litwalk, target, skip_check):
    """
    Add a .bib file or DOI
    """
    # DOI regex
    # https://www.crossref.org/blog/dois-and-matching-regular-expressions/
    doi_regex = re.compile(r"/^10.\d{4,9}/[-._;()/:A-Z0-9]+$/")

    # add .bib file
    if target.endswith(".bib"):

        # check specified path
        if not os.path.exists(target):
            raise Exception("No Bibtex file found at specified path!")

        print(f"Scanning {target} for new entries...")
        litwalk.import_bibtex(target, skip_check=skip_check)

    # TODO: add single article by DOI
    elif doi_regex.match(target):
        logger.info("DOI support not yet implemented..")

@cli.command
@click.pass_obj
def info(litwalk):
    """Display lit collection info"""
    info_:dict[str, Any] = litwalk.info()

    print(f"[sky_blue1]# Articles[/sky_blue1]: {info_['num_articles']}")
    print("[salmon1]Incomplete Metadata[/salmon1]:")
    print(f"[light_salmon1]- Missing \"DOI\":[/light_salmon1] {info_['missing']['doi']}")
    print(f"[light_salmon1]- Missing \"abstract\":[/light_salmon1] {info_['missing']['abstract']}")
    print(f"[light_salmon1]- Missing \"keywords\":[/light_salmon1] {info_['missing']['keywords']}")

@cli.command
@click.argument("query", default="", type=str)
@click.pass_obj
def walk(litwalk, query:str):
    """
    Stochastic article suggestion
    """
    res = litwalk.walk(query)

    article = res['article']

    if query != "":
        print(f"[sky_blue1]Including {res['num_filtered']}/{res['num_articles']} articles...[/sky_blue1]")

    year_str = f"[light_goldenrod3]{article['year']}[/light_goldenrod3]"
    print(f"[bold light_coral]{article['title']}[/bold light_coral] ({year_str})")
    print(f"[bold light_salmon1]{article['author']}[/bold light_salmon1]")

    if article['abstract'] is not None:
        print(Padding(article['abstract'], (1, 1), style='grey89'))

    print(f"[sea_green1] - url[/sea_green1]: {article['url']}")
    print(f"[sea_green1] - doi[/sea_green1]: {article['doi']}")

def run():
    """Initialize and run CLI"""
    #  from litwalk.cli import LitCLI
    #  LitCLI()
    cli()
