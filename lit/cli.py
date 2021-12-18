"""
lit-tool CLI
"""
import os
import sys
import datetime
import logging
from argparse import ArgumentParser
from lit.tool import LitTool


class LitCLI:
    def __init__(self):
        """Initializes a new LitCLI instance"""
        self._setup_logger()

        logging.info("Initializing lit...")

        # initialize lit
        self.lit = LitTool()

        self._get_args()

    def _setup_logger(self):
        """Sets up root logger to print messages to STDOUT"""
        # credit: https://stackoverflow.com/a/14058475/554531
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        root.addHandler(handler)

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
   walk     [NOT IMPLEMENTED] Randomly suggests an article for review
   stats    [NOT IMPLEMENTED] Display user review stats
''')

        parser.add_argument('command', help='Sub-command to run')
        
        # parse and validate sub-command
        args = parser.parse_args(sys.argv[1:2])

        valid_cmds = ['walk', 'add', 'stats']

        if args.command not in valid_cmds:
            logging.error("Unrecognized command specified: {args.command}!")
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

        # parse remaining parts of command args
        args = parser.parse_args(sys.argv[2:])

        # check specified path
        if not os.path.exists(args.bibtex):
            raise Exception("No Bibtex file found at specified path!")
        elif not args.bibtex.endswith(".bib"):
            raise Exception("Invalid input! Expecting a .bib file...")

        # import and add any new entries to db
        self.lit.import_bibtex(args.bibtex)

    def walk(self):
        """
        "walk" command
        """
        # parse "walk"-specific args
        parser = ArgumentParser(description='Randomly suggests an article for review')

        parser.add_argument(
            "-t",
            "--topics",
            help="Specific topic(s) to choose from",
            type=str
        )

        # parse remaining parts of command args
        args = parser.parse_args(sys.argv[2:])

    def stats(self):
        """
        "stats" command
        """
        # parse "stats"-specific args
        parser = ArgumentParser(description='Display user stats')

        # parse remaining parts of command args
        args = parser.parse_args(sys.argv[2:])
