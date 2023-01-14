"""
LitWalk Class definition
"""
import datetime
import logging
import os
import pandas as pd
import random
import re
import shutil
import sqlite3
import sys
import yaml
import bibtexparser
from typing import Any, TypedDict
from bibtexparser.bparser import BibTexParser
from pkg_resources import resource_filename
from rich import print
from . notesmanager import NotesManager

__version__ = "0.3.0"

class ArticleResult(TypedDict):
    article: dict[str, Any]
    num_included: int
    num_total: int

class LitWalk:
    """
    LitWalk class definition
    """
    def __init__(self, config:str, verbose:bool):
        """
        Initializes a new LitWalk instance.

        Parameters
        ----------
        config: str
            Path to lit-walk configuration file
        verbose: bool
            If True, verbose logging is enabled
        """
        # setting logging
        self.verbose = verbose
        self._setup_logger()

        # load config
        self._load_config(config)

        # load articles / stats databases
        self._init_db()

        # initialize notes manager
        self._notes = NotesManager(self._config["notes_dir"])

    def _setup_logger(self):
        """
        Sets up logger to print messages to STDOUT
        """
        logging.basicConfig(stream=sys.stdout,
                            format='[%(levelname)s] %(message)s')

        self._logger = logging.getLogger('lit-walk')

        if self.verbose:
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.WARN)

    def _init_db(self):
        """
        Initializes database with user articles/stats.

        If the database does not already exist, it will be created.
        """
        dbpath = os.path.join(self._config['data_dir'], 'db.sqlite')
        dbpath = os.path.realpath(os.path.expanduser(os.path.expandvars(dbpath)))

        if not os.path.exists(self._config['data_dir']):
            os.makedirs(os.path.expanduser(self._config['data_dir']), mode=0o755)

        # connect to db
        try:
            self.db = sqlite3.connect(dbpath)
        except sqlite3.Error as exception:
            print(exception)

        cursor = self.db.cursor()

        # get a list of tables in the db
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [x[0] for x in cursor.fetchall()]

        if "articles" not in tables:
            self._create_articles_table(cursor)

        if "activity" not in tables:
            self._create_activity_table(cursor)

        if "articleTopics" not in tables:
            self._create_article_topics_table(cursor)

        cursor.close()

    def _create_articles_table(self, cursor:sqlite3.Cursor):
        """
        Creates articles table.

        Structure modeled after paperpile, to simplify communication between the two.
        """
        sql = """
        CREATE TABLE IF NOT EXISTS articles (
            id integer PRIMARY KEY,
            doi text,
            isbn text,
            issn text,
            pmc text,
            pmid integer,
            arxivid text,
            title text NOT NULL,
            abstract text,
            booktitle text,
            edition text,
            entrytype text,
            journal text,
            keywords text,
            pages text,
            author text,
            volume text,
            number text,
            url text,
            year integer,
            month integer
        );
        """
        self._logger.info("Creating articles table...")

        try:
            cursor.execute(sql)
        except sqlite3.Error as e:
            print(e)

    def _create_activity_table(self, cursor:sqlite3.Cursor):
        """
        Creates activity table.

        ACTIONS

        0 add
        1 view
        2 modify
        3 remove
        4 note
        """
        sql = """
        CREATE TABLE IF NOT EXISTS activity (
            id integer PRIMARY KEY,
            date timestamp,
            action integer DEFAULT 0
        );
        """
        self._logger.info("Creating stats table...")

        try:
            cursor.execute(sql)
        except sqlite3.Error as e:
            print(e)

    def _create_article_topics_table(self, cursor:sqlite3.Cursor):
        """
        Creates a table mapping from article to topics
        """
        sql = """
        CREATE TABLE IF NOT EXISTS articleTopics (
            id integer PRIMARY KEY,
            doi text,
            topic text
        );
        """
        self._logger.info("Creating article-topics table...")

        try:
            cursor.execute(sql)
        except sqlite3.Error as e:
            print(e)

    def get_article_texts(self, exclude_missing=True):
        """
        Returns a dict mapping from article DOIs to concatenated titles + abstracts.
        """
        # get article titles + abstracts
        cursor = self.db.cursor()

        sql = "SELECT doi, title, abstract FROM articles ORDER BY doi"

        if self._config['dev_mode']['enabled']:
            sql += f" LIMIT {self._config['dev_mode']['subsample']}"

        res = cursor.execute(sql)
        articles = cursor.fetchall()

        article_texts = {}

        for article in articles:
            # if enabled, skip articles with missing abstracts
            if exclude_missing and article[2] is None:
                continue

            article_texts[article[0]] = article[1] + article[2]

        return article_texts

    def get_doi(self, cursor:sqlite3.Cursor) -> list[str]:
        """
        Returns a list of existing DOIs in the database
        """
        sql = "SELECT doi FROM articles"

        if self._config['dev_mode']['enabled']:
            sql += f" LIMIT {self._config['dev_mode']['subsample']}"

        cursor.execute(sql)

        return [x[0] for x in cursor.fetchall()]

    def get_articles(self, n=None, missing_abstracts=False) -> list[dict[str, Any]]:
        """
        Retrieves articles table

        Parameters
        ----------
        n: int|None
            Number of articles to retrieve; if "None", returns all (default: None)
        missing_abstracts: bool
            If true, only include articles with missing abstracts (default: False)
        """
        cursor = self.db.cursor()

        # all articles
        if n is None:
            if missing_abstracts:
                sql = "SELECT * FROM articles WHERE abstract IS NULL;"
            else:
                sql = "SELECT * FROM articles;"
        else:
            if self._config['dev_mode']['enabled']:
                n = min(n, self._config['dev_mode']['subsample'])

            # subset of articles
            if missing_abstracts:
                sql = f"""SELECT * FROM articles WHERE id IN
                           (SELECT id FROM articles WHERE abstract IS NULL
                            ORDER BY RANDOM() LIMIT {n})"""
            else:
                sql = f"""SELECT * FROM articles WHERE id IN (SELECT id FROM articles ORDER BY
                                                              RANDOM() LIMIT {n})"""

        res = cursor.execute(sql)

        articles = cursor.fetchall()

        colnames = [x[0] for x in res.description]

        article_dicts = []

        for article in articles:
            article_dicts.append(dict(zip(colnames, article)))

        return article_dicts

    def walk(self, search=""):
        """Chooses an article at random"""
        # if no search constraints specified, choose from all articles
        if search == "":
            res = self.get_random()
        else:
            res = self.get_filtered(search)

        # update stats; for now, assume article was read (later: prompt user..)
        self.update_stats(res['article']["doi"])

        return res

    def get_filtered(self, search="") -> ArticleResult:
        """
        Gets a single random article, limited to those matching some specified search
        phrase
        """
        articles = self.get_articles()

        filtered = []

        num_articles = len(articles)

        # force case-insensitive comparison, for now.
        search = search.lower()

        for article in articles:
            for field in ['abstract', 'author', 'keywords', 'title']:
                if article[field] is None:
                    continue

                if search in article[field].lower():
                    filtered.append(article)

        num_filtered = len(filtered)

        res:ArticleResult = {
            "article": random.sample(filtered, 1)[0],
            "num_included": num_filtered,
            "num_total": num_articles
        }

        return res

    def get_random(self) -> ArticleResult:
        """
        Gets a single random article from among all articles
        """
        cursor = self.db.cursor()

        num_articles = self.num_articles()

        if num_articles == 0:
            raise Exception("No articles found!")

        ind = random.randint(1, num_articles)

        res = cursor.execute(f"SELECT * FROM articles WHERE id={ind};")
        article = cursor.fetchall()[0]
        colnames = [x[0] for x in res.description]
        article = dict(zip(colnames, article))
        cursor.close()

        res:ArticleResult = {
            "article": article,
            "num_included": num_articles,
            "num_total": num_articles
        }

        return res

    def update_stats(self, doi):
        """Add entry to stats table"""
        cursor = self.db.cursor()

        res = cursor.execute("INSERT INTO stats(doi, date) VALUES (?, ?);",
                          (doi, datetime.datetime.now()))
        self.db.commit()
        cursor.close()

    def import_bibtex(self, infile:str, skip_check=False):
        """
        Imports and parses a bibtex reference file
        """
        self._logger.info(f"Importing references from BibTeX file: {infile}")

        if not os.path.exists(infile):
            raise Exception("No Bibtex file found at specified path!")

        with open(infile) as bibtex_file:
            parser = BibTexParser(common_strings = True)
            bibtex = bibtexparser.load(bibtex_file, parser=parser)

        # for now, exclude any entries with no associated DOI..
        articles = [x for x in bibtex.entries if "doi" in x]

        if len(articles) < len(bibtex.entries):
            num_missing = len(bibtex.entries) - len(articles)
            self._logger.warn(f"Excluding {num_missing} articles with no associated DOI")

        cursor = self.db.cursor()

        # exclude existing articles
        if not skip_check:
            existing_dois = self.get_doi(cursor)

            num_before = len(articles)
            articles = [x for x in articles if x['doi'] not in existing_dois]
            num_after = len(articles)

            if num_before != num_after:
                num_removed = num_before - num_after
                self._logger.warn("Excluding %s articles already present in collection", num_removed)
        else:
            num_after = len(articles)

        # drop any articles that already exist in the database;
        # in the future, may be useful to support _updating_ existing entries..
        if num_after > 0:
            self._logger.info("Adding %s new articles..", num_after)

            self.add_articles(articles, cursor)
        else:
            self._logger.info("No new articles found..")

        cursor.close()

    def add_articles(self, articles:list[dict[str, str]], cursor:sqlite3.Cursor):
        """
        Adds one or more articles to the users collection

        articles: list[dict]
            List of article dicts as returned from sqlite query
        cursor: sqlite3.Cursor
            sqlite3 db cursor
        """
        fields = ["doi", "booktitle", "edition", "entrytype", "isbn", "issn", "journal",
                  "keywords", "pmc", "pmid", "title", "abstract", "author", "file",
                  "volume", "number", "url", "year"]

        for article in articles:
            entry = {k: None for k in fields}
            captured_fields = {k: article[k] for k in fields if k in article}

            entry.update(captured_fields)

            # strip newlines from title, abstract, keywords, etc.
            for field in ['title', 'abstract', 'author', 'keywords']:
                if entry[field] is not None:
                    entry[field] = entry[field].replace("\n", " ")

            # extract keywords;
            if entry['keywords'] is not None:
                keywords = []

                for keyword in entry['keywords'].split(";"):
                    # for now, store all keywords as lowercase (better for matching
                    # in article abstracts, etc.)
                    keyword = keyword.strip().lower()

                    # exclude keywords that contain a "/", possibly corresponding to a path in
                    # paperpile (this can be made optional, in the future..)
                    if "/" not in keyword:
                        keywords.append(keyword)

                entry['keywords'] = "; ".join(keywords)

            self.add_article(cursor, tuple(entry.values()))

        self._logger.info("Finished!")

    def add_article(self, cursor:sqlite3.Cursor, article:tuple[str]):
        """
        Adds a single article to a user's collection

        """
        sql = '''INSERT INTO articles(doi, booktitle, edition, entrytype, isbn, issn, journal,
                                      keywords, pmc, pmid, title, abstract, author, file, volume,
                                      number, url, year)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        cursor.execute(sql, article)

        self.db.commit()

    def info(self):
        """
        Returns basic information about lit setup.

        Note that that info command does ignores "dev_mode", if enabled.
        """
        # determine how many articles are missing doi/absract/keywords
        cursor = self.db.cursor()

        # count # articles with missing DOIs
        sql = "SELECT COUNT(*) FROM articles WHERE doi IS NULL"
        missing_doi = cursor.execute(sql).fetchall()[0][0]

        # count # articles with missing abstracts
        sql2 = "SELECT COUNT(*) FROM articles WHERE abstract IS NULL"
        missing_abstract = cursor.execute(sql2).fetchall()[0][0]

        # count # articles with missing keywords
        sql3 = "SELECT COUNT(*) FROM articles WHERE keywords IS NULL"
        missing_keywords = cursor.execute(sql3).fetchall()[0][0]

        cursor.close()

        return {
            "num_articles": self.num_articles(),
            "missing": {
                "doi": missing_doi,
                "abstract": missing_abstract,
                "keywords": missing_keywords
            }
        }

    def num_articles(self):
        """
        Returns the number of articles present in the user's collection
        """
        cursor = self.db.cursor()

        sql = "SELECT COUNT(id) FROM articles;"

        if self._config['dev_mode']['enabled']:
            sql += f" LIMIT {self._config['dev_mode']['subsample']}"

        cursor.execute(sql)
        num_articles = cursor.fetchall()[0][0]

        cursor.close()

        return num_articles

    def _load_config(self, config:str):
        """
        Loads user config / creates one if none exists
        """
        infile = os.path.expanduser(config)

        if not os.path.exists(infile):
            self._logger.info("Generating a new configuration at %s...", infile)
            self._create_config(infile)

        with open(infile, "rt", encoding="utf-8") as fp:
            self._config = yaml.load(fp, Loader=yaml.FullLoader)

        # apply any arguments passed in
        #self._config.update(kwargs)

    def _create_config(self, config_file:str):
        """
        Generates a default config file
        """
        conf_dir = os.path.dirname(config_file)

        if not os.path.exists(conf_dir):
            os.makedirs(conf_dir, mode=0o755)

        default_conf = os.path.join(os.path.abspath(resource_filename(__name__, "conf")), "default.yml")

        shutil.copy(default_conf, config_file)

        self._logger.info(f"Default config file generated at {config_file}")
