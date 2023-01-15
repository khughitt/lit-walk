"""
lit-walk CLI
"""
import json
import os
import re
import sys
import datetime
import logging
import shutil
import yaml
import click
from typing import Any
from litwalk import LitWalk
from litwalk.views import NotesView
from rich import print
from rich.padding import Padding
from rich.table import Table
from pkg_resources import resource_filename

# initialize logger
logging.basicConfig(stream=sys.stdout, format='[%(levelname)s] %(message)s')
logger = logging.getLogger('lit-walk')

# print header
print("[cyan]========================================[/cyan]")
print(":books:", "[bold orchid]lit-walk[/bold orchid]")
print("[cyan]========================================[/cyan]")

# determine default config path to use
if os.getenv('XDG_CONFIG_HOME'):
    conf_dir = os.path.join(str(os.getenv("XDG_CONFIG_HOME")), "lit-walk")
elif os.getenv('HOME'):
    conf_dir = os.path.join(str(os.getenv("HOME")), ".lit-walk")
else:
    raise Exception("Unable to infer location of config file automatically")

default_config_path = os.path.join(conf_dir, "config.yml")

@click.group()
@click.option("--config", default=default_config_path, help="Path to lit-walk config file to use")
@click.option("--verbose", is_flag=True, help="If enabled, prints verbose output")
@click.pass_context
def cli(ctx, config:str, verbose:bool):
    """Initialize CLI"""
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARN)

    logger.info("Initializing lit-walk...")

    # copy default config, if none found
    if not os.path.exists(config):
        if not os.path.exists(conf_dir):
            os.makedirs(conf_dir, mode=0o755)

        default_cfg = os.path.join(os.path.abspath(
            resource_filename(__name__, "conf")), "default.yml")
        shutil.copy(default_cfg, config)
        logger.info("Default config file generated at %s", config)

    config = os.path.expanduser(config)

    with open(config, "rt", encoding="utf-8") as fp:
        cfg = yaml.load(fp, Loader=yaml.FullLoader)

    # initialize lit
    ctx.obj = LitWalk(verbose=verbose, **cfg)

@cli.command
@click.argument("target", type=str)
@click.pass_obj
def add(litwalk, target):
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
        litwalk.import_bibtex(target)

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
@click.pass_obj
def notes(litwalk):
    """Take notes on an article"""
    articles = litwalk.get_articles()
    view = NotesView(articles, litwalk.get_notes_dir())
    view.run()

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
