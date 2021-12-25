"""
LitTool Class definition
"""
import re
import random
import os
import yaml
import logging
import sqlite3
import sys
import bibtexparser
from bibtexparser.bparser import BibTexParser

class LitTool:
    def __init__(self):
        """Initializes a new LitTool instance."""
        # setting logging
        self._setup_logger()

        # config dir
        if os.getenv('XDG_CONFIG_HOME'):
            self._conf_dir = os.path.join(str(os.getenv("XDG_CONFIG_HOME")), "lit")
        elif os.getenv('HOME'):
            self._conf_dir = os.path.join(str(os.getenv("HOME")), ".lit")
        else:
            raise Exception("Unable to infer location of config file automatically")
            sys.exit()

        # load config
        self._load_config()

        # load articles / stats databases
        self._init_db()

    def _setup_logger(self):
        """Sets up logger to print messages to STDOUT"""
        logging.basicConfig(stream=sys.stdout, 
                            format='[%(levelname)s] %(message)s')

        self._logger = logging.getLogger('lit')
        self._logger.setLevel(logging.DEBUG)

    def _init_db(self):
        """
        Initializes database with user articles/stats.

        If the database does not already exist, it will be created.
        """
        dbpath = os.path.join(self._config['data_dir'], 'db.sqlite')

        if not os.path.exists(self._config['data_dir']):
            os.makedirs(self._config['data_dir'], mode=0o755)

        # connect to db
        try:
            self.db = sqlite3.connect(dbpath)
        except sqlite3.Error as e:
            print(e)

        cursor = self.db.cursor()

        # get a list of tables in the db
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [x[0] for x in cursor.fetchall()]

        if "articles" not in tables:
            self._create_articles_table(cursor)

        if "stats" not in tables:
            self._create_stats_table(cursor)

        cursor.close()

    #  def sync(self):
    #      """
    #      Sync lit-tool db & update stats
    #
    #      1. add/extend keywords
    #      """
    #      pass

    def update_keywords(self):
        """
        Updates and extends keywords associated with each article.

        First, a list of all keywords associated with at least one article is
        inferred.

        Next, the title/abstract of each article is scanned, and any detected keywords which are not already prese

        TODO:
        - limit to keywords that appear at least N times?
        - lemmatize keywords and check for keywords in lemmatized space?
        """

    def _create_articles_table(self, cursor):
        """
        Creates articles table.

        Structure modeled after paperpile, to simplify communication between the two.
        """
        sql = """
        CREATE TABLE IF NOT EXISTS articles (
            id integer PRIMARY KEY,
            doi text NOT NULL,
            booktitle text,
            edition text,
            entrytype text,
            isbn text,
            issn text,
            journal text,
            keywords text,
            pmc text,
            pmid integer,
            title text NOT NULL,
            abstract text,
            author text,
            file text,
            volume text,
            number text,
            url text,
            year integer,
            times_read integer DEFAULT 0 NOT NULL
        );
        """
        self._logger.info("Creating articles table...")

        try:
            cursor.execute(sql)
        except sqlite3.Error as e:
            print(e)

    def _create_stats_table(self, cursor):
        """
        Creates user stats table.
        """
        sql = """
        CREATE TABLE IF NOT EXISTS stats (
            id integer PRIMARY KEY,
            topic text,
            num_articles integer,
            times_reviewed integer
        );
        """
        self._logger.info("Creating stats table...")

        try:
            cursor.execute(sql)
        except sqlite3.Error as e:
            print(e)

    def _create_topics_table(self, cursor):
        """
        Create and <article x topic> matrix?
            - since topics will change across time, perhaps store in "long" form in sql?
        """
        sql = """
        CREATE TABLE IF NOT EXISTS topics (
            id integer PRIMARY KEY,
            topic text,
            num_articles integer,
            times_reviewed integer
        );
        """
        self._logger.info("Creating topics table...")

        try:
            cursor.execute(sql)
        except sqlite3.Error as e:
            print(e)

    #  def _sync_topics(self, articles):
    def _sync_topics(self):
        """
        Scans article collection and updates topics table.
        """
        articles = self.get_articles()

        breakpoint()

    def get_articles(self):
        """Retrieves articles table"""
        cur = self.db.cursor()

        res = cur.execute("SELECT * FROM articles;")

        articles = cur.fetchall()

        colnames = [x[0] for x in res.description]

        article_dicts = []

        for article in articles:
            article_dicts.append(dict(zip(colnames, article)))

        return article_dicts

    def walk(self):
        """Chooses an article at random"""
        num_articles = self.num_articles()

        ind = random.randint(1, num_articles)

        cur = self.db.cursor()

        res = cur.execute(f"SELECT * FROM articles WHERE id={ind};")
        article = cur.fetchall()[0]
        colnames = [x[0] for x in res.description]
        article = dict(zip(colnames, article))

        cur.close()

        return article 

    def import_bibtex(self, infile, debug=False):
        """
        Imports and parses a bibtex reference file
        """
        self._logger.info(f"Importing references from BibTeX file: {infile}")

        if not os.path.exists(infile):
            raise Exception("No Bibtex file found at specified path!")

        with open(infile) as bibtex_file:
            parser = BibTexParser(common_strings = True)
            bd = bibtexparser.load(bibtex_file, parser=parser)

        # for now, exclude any entries with no associated DOI..
        articles = [x for x in bd.entries if "doi" in x]

        if len(articles) < len(bd.entries):
            num_missing = len(bd.entries) - len(articles)
            self._logger.warn(f"Excluding {num_missing} articles with no associated DOI")

        # exclude existing articles
        if not debug:
            cur = self.db.cursor()
            cur.execute("SELECT doi FROM articles;")
            
            existing_dois = cur.fetchall()

            num_before = len(articles)
            articles = [x for x in articles if x['doi'] not in existing_dois]
            num_after = len(articles)

            if num_before != num_after:
                num_removed = num_before - num_after
                self._logger.warn(f"Excluding {num_removed} articles already present in collection")
        else:
            num_after = len(articles)

        # drop any articles that already exist in the database;
        # in the future, may be useful to support _updating_ existing entries..
        if num_after > 0:
            self._logger.info(f"Adding {num_after} new articles..")

            fields = ["doi", "booktitle", "edition", "entrytype", "isbn", "issn", "journal",
                    "keywords", "pmc", "pmid", "title", "abstract", "author", "file",
                    "volume", "number", "url", "year"]

            for article in articles:
                entry = {k: None for k in fields}
                captured_fields = {k: article[k] for k in fields if k in article}

                entry.update(captured_fields)

                self.add_article(cur, tuple(entry.values()))
            
            self._logger.info(f"Finished!")

            #  self._sync_topics(articles)
            self._sync_topics()

        cur.close()

    def add_article(self, cursor, article):
        sql = '''INSERT INTO articles(doi, booktitle, edition, entrytype, isbn, issn, journal, keywords, pmc, pmid, title, abstract, author, file, volume, number, url, year)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        cursor.execute(sql, article)

        self.db.commit()

    def info(self):
        """Returns basic information about lit setup"""
        # determine how many articles are missing doi/absract/keywords
        cur = self.db.cursor()

        missing_doi = cur.execute("SELECT COUNT(*) FROM articles WHERE doi IS NULL;").fetchall()[0][0]
        missing_abstract = cur.execute("SELECT COUNT(*) FROM articles WHERE abstract IS NULL;").fetchall()[0][0]
        missing_keywords = cur.execute("SELECT COUNT(*) FROM articles WHERE keywords IS NULL;").fetchall()[0][0]

        cur.close()

        return {
            "num_articles": self.num_articles(),
            "missing": {
                "doi": missing_doi,
                "abstract": missing_abstract,
                "keywords": missing_keywords
            }
        }

    def num_articles(self):
        """Returns the number of articles present in the user's collection"""
        cur = self.db.cursor()
        cur.execute("SELECT COUNT(id) FROM articles;")

        num_articles = cur.fetchall()[0][0]

        cur.close()

        return num_articles

    def _load_config(self):
        """Loads user config / creates one if none exists"""
        infile = os.path.expanduser(os.path.join(self._conf_dir, "config.yml"))

        if not os.path.exists(infile):
            self._logger.info(f"Generating a new configuration at {infile}...")
            self._create_config(infile)

        with open(infile) as fp:
            self._config = yaml.load(fp, Loader=yaml.FullLoader)

        # apply any arguments passed in
        #self._config.update(kwargs)

    def _create_config(self, config_file):
        """
        Generates a default config file
        """
        conf_dir = os.path.dirname(config_file)

        if not os.path.exists(conf_dir):
            os.makedirs(conf_dir, mode=0o755)

        with open(config_file, 'w') as fp:
            yaml.dump(self._default_config(), fp)

    def _default_config(self):
        """
        Returns default configuration as a dict
        """
        return {
            "data_dir": os.path.join(str(os.getenv("HOME")), ".lit")
        }

