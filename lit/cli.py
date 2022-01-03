"""
lit-walk CLI
"""
import os
import sys
import datetime
import logging
from argparse import ArgumentParser
from lit.walk import LitWalk
from rich import print
#from rich.markdown import Markdown

class LitCLI:
    def __init__(self):
        """Initializes a new LitCLI instance"""
        self._setup_logger()

        self._logger.info("Initializing lit...")

        # initialize lit
        self.lit = LitWalk(cli_mode=True)

        self._get_args()

    def _setup_logger(self):
        """Sets up logger to print messages to STDOUT"""
        """Sets up logger to print messages to STDOUT"""
        logging.basicConfig(stream=sys.stdout, 
                            format='[%(levelname)s] %(message)s')

        self._logger = logging.getLogger('lit')
        self._logger.setLevel(logging.DEBUG)

    def _get_args(self):
        """
        Parses input and returns arguments

        Based on: https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html
        """
        parser = ArgumentParser(
            description="Tools to help with understanding the scientific literature",
            usage='''lit <command> [<args>]

List of supported commands:
   add      Adds a .bib BibTeX reference collection
   info     Display lit collection info
   walk     Randomly suggests an article for review
   stats    [NOT IMPLEMENTED] Display user review stats
''')

        parser.add_argument('command', help='Sub-command to run')
        
        # parse and validate sub-command
        args = parser.parse_args(sys.argv[1:2])

        valid_cmds = ['walk', 'add', 'info', 'stats']

        if args.command not in valid_cmds:
            self._logger.error("Unrecognized command specified: {args.command}!")
            parser.print_help()
            sys.exit()

        # execute method with same name as sub-command
        getattr(self, args.command)()

    def add(self):
        """
        "add" command
        """
        parser = ArgumentParser(description='Add a .bib BibTeX reference collection')

        parser.add_argument(
            "bibtex",
            nargs="?",
            type=str,
            help="Path to .bib file to be imported",
        )

        parser.add_argument(
            "-d",
            "--debug",
            help="If enabled, skips check for existing articles",
            action="store_true",
        )

        # parse remaining parts of command args
        args = parser.parse_args(sys.argv[2:])

        # check specified path
        if not os.path.exists(args.bibtex):
            raise Exception("No Bibtex file found at specified path!")
        elif not args.bibtex.endswith(".bib"):
            raise Exception("Invalid input! Expecting a .bib file...")

        # import and add any new entries to db
        self.lit.import_bibtex(args.bibtex, debug=args.debug)

    def walk(self):
        """
        "walk" command
        """
        # parse "walk"-specific args
        parser = ArgumentParser(description='Randomly suggests an article for review')

        parser.add_argument(
            "-s",
            "--search",
            help="Limit search to articles containing the specified search phrase",
            default="",
            type=str
        )

        # parse remaining parts of command args
        args = parser.parse_args(sys.argv[2:])

        article = self.lit.walk(args.search)

        self._print_header()
        
        year_str = f"[light_goldenrod3]{article['year']}[/light_goldenrod3]"
        print(f"[sky_blue1]Article[/sky_blue1]: {article['title']} ({year_str})")

        print(f"[sea_green1] - url[/sea_green1]: {article['url']}")
        print(f"[sea_green1] - doi[/sea_green1]: {article['doi']}")

    def _print_header(self):
        """
        prints lit-walk header
        """
        print("[cyan]========================================[/cyan]")
        print(":books:", "[bold orchid]lit-walk[/bold orchid]")
        print("[cyan]========================================[/cyan]")

    def info(self):
        """
        "info" command
        """
        parser = ArgumentParser(description='Display lit collection info')

        # parse remaining parts of command args
        args = parser.parse_args(sys.argv[2:])

        info = self.lit.info()

        self._print_header()
        print(f"[sky_blue1]# Articles[/sky_blue1]: {info['num_articles']}")
        print(f"[salmon1]Incomplete Metadata[/salmon1]:")
        print(f"[light_salmon1]- Missing \"DOI\":[/light_salmon1]: {info['missing']['doi']}")
        print(f"[light_salmon1]- Missing \"abstract\":[/light_salmon1]: {info['missing']['abstract']}")
        print(f"[light_salmon1]- Missing \"keywords\":[/light_salmon1]: {info['missing']['keywords']}")

    def stats(self):
        """
        "stats" command
        """
        # parse "stats"-specific args
        parser = ArgumentParser(description='Display user stats')

        # parse remaining parts of command args
        args = parser.parse_args(sys.argv[2:])
