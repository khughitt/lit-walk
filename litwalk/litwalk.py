"""
LitWalk Class definition
"""
import datetime
import hashlib
import logging
import os
import random
import re
import sqlite3
import string
import sys
import bibtexparser
from typing import Any, TypedDict
from bibtexparser.bparser import BibTexParser
from rich import print

__version__ = "0.3.0"

class ArticleResult(TypedDict):
    article: dict[str, Any]
    num_included: int
    num_total: int

# activity codes
ACTIVITY_ADD = 0
ACTIVITY_VIEW = 1
ACTIVITY_MODIFY = 2
ACTIVITY_REMOVE = 3
ACTIVITY_NOTE = 4
ACTIVITY_WALK = 5

class LitWalk:
    """
    LitWalk class definition
    """
    def __init__(self, data_dir:str, notes_dir:str, dev_mode=False, dev_mode_subsample=100,
                 verbose=False):
        """
        Initializes a new LitWalk instance.

        Parameters
        ----------
        verbose: bool
            If True, verbose logging is enabled
        """
        self.data_dir = data_dir
        self.notes_dir = notes_dir
        self.dev_mode = dev_mode
        self.dev_mode_subsample = dev_mode_subsample
        self.verbose = verbose

        # setting logging
        self._setup_logger()

        # create data and notes directories, if needed
        if not os.path.exists(self.data_dir):
            os.makedirs(os.path.expanduser(self.data_dir), mode=0o755)

        if not os.path.exists(self.notes_dir):
            os.makedirs(os.path.expanduser(self.notes_dir), mode=0o755)

        # initialize database
        self._init_db()

    def get_notes_dir(self) -> str:
        """Returns path to base user notes directory"""
        return self.notes_dir

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
        Initializes database

        If the database does not already exist, it will be created.
        """
        dbpath = os.path.join(self.data_dir, 'db.sqlite')
        dbpath = os.path.realpath(os.path.expanduser(os.path.expandvars(dbpath)))

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

        if "annotations" not in tables:
            self._create_annot_table(cursor)

        if "articleAnnot" not in tables:
            self._create_article_annot_table(cursor)

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
            note text,
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
            month integer,
            md5 text
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
        """
        sql = """
        CREATE TABLE IF NOT EXISTS activity (
            id integer PRIMARY KEY,
            entity_id INT,
            date timestamp,
            action integer DEFAULT 0
        );
        """
        self._logger.info("Creating activity table...")

        try:
            cursor.execute(sql)
        except sqlite3.Error as e:
            print(e)

    def _create_annot_table(self, cursor:sqlite3.Cursor):
        """
        Creates annotation table.
        """
        sql = """
        CREATE TABLE IF NOT EXISTS annotations (
            id integer PRIMARY KEY,
            title text,
            note text,
            description text,
            source text
        );
        """
        self._logger.info("Creating annotations table...")

        try:
            cursor.execute(sql)
        except sqlite3.Error as e:
            print(e)

    def _create_article_annot_table(self, cursor:sqlite3.Cursor):
        """
        Creates a table mapping from article to topics
        """
        sql = """
        CREATE TABLE IF NOT EXISTS articleAnnot (
            id integer PRIMARY KEY,
            article_id integer NOT NULL,
            annot_id integer NOT NULL,
            start integer,
            end integer
        );
        """
        self._logger.info("Creating articleAnnot table...")

        try:
            cursor.execute(sql)
        except sqlite3.Error as e:
            print(e)

    def get_md5s(self, cursor:sqlite3.Cursor) -> list[str]:
        """
        Returns a list of existing md5sums in the database
        """
        cursor.execute("SELECT md5 FROM articles")

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
            if self.dev_mode:
                n = min(n, self.dev_mode_subsample)

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

        # update activity
        self.update_activity(res['article']["id"], ACTIVITY_WALK)

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

    def update_activity(self, entity_id, action=ACTIVITY_ADD):
        """
        Add entry to activity table
        """
        cursor = self.db.cursor()

        res = cursor.execute("INSERT INTO activity(entity_id, date, action) VALUES (?, ?, ?);",
                             (entity_id, datetime.datetime.now(), action))
        self.db.commit()
        cursor.close()

    def import_bibtex(self, infile:str):
        """
        Imports and parses a bibtex reference file
        """
        self._logger.info(f"Importing references from BibTeX file: {infile}")

        if not os.path.exists(infile):
            raise Exception("No Bibtex file found at specified path!")

        with open(infile) as bibtex_file:
            parser = BibTexParser(common_strings = True)
            bibtex = bibtexparser.load(bibtex_file, parser=parser)

        articles = bibtex.entries

        # skip any entries which are missing both title & abstract
        num_before = len(articles)

        self._logger.info(f"Checking {num_before} entries..")

        articles = [x for x in articles if "title" in x or "abstract" in x]

        num_after = len(articles)

        if num_before != num_after:
            num_removed = num_before - num_after
            self._logger.warn("Excluding %s articles missing both title & abstract fields",
                              num_removed)

        # compute md5 hash for each article title + abstract
        for article in articles:
            title = article.get("title", "")
            abstract = article.get("abstract", "")

            hash_input = (title + abstract).encode("utf-8")
            article['md5'] = hashlib.md5(hash_input).hexdigest()

        # exclude articles already present in the db
        cursor = self.db.cursor()
        existing_md5s = self.get_md5s(cursor)

        num_before = len(articles)
        articles = [x for x in articles if x['md5'] not in existing_md5s]
        num_after = len(articles)

        if num_before != num_after:
            num_removed = num_before - num_after
            self._logger.warn("Excluding %s articles already present in collection", num_removed)

        # determine note path to use for article
        for article in articles:
            article["note"] = self._get_note_path(article, cursor)

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
        fields = ["doi", "isbn", "issn", "pmc", "pmid", "arxivid", "title", "abstract", "note",
                  "booktitle", "edition", "entrytype", "journal", "keywords", "pages", "author",
                  "volume", "number", "url", "year", "month", "md5"]

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
        sql = '''INSERT INTO articles(doi, isbn, issn, pmc, pmid, arxivid, title, abstract, note,
                                      booktitle, edition, entrytype, journal, keywords, pages,
                                      author, volume, number, url, year, month, md5)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        cursor.execute(sql, article)

        self.db.commit()

    def info(self) -> dict[str,Any]:
        """
        Returns basic information about user article collection
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

    def num_articles(self) -> int:
        """
        Returns the number of articles present in the user's collection
        """
        cursor = self.db.cursor()

        sql = "SELECT COUNT(id) FROM articles;"

        if self.dev_mode:
            sql += f" LIMIT {self.dev_mode_subsample}"

        cursor.execute(sql)
        num_articles = cursor.fetchall()[0][0]

        cursor.close()

        return num_articles

    def _get_note_path(self, article:dict[str, str], cursor:sqlite3.Cursor) -> str:
        """
        Determines path to use for markdown note associated with an article

        Path: <first author initial>/<first author><year>_<title><optional multiple suffix>
        """
        year = article.get("year", "")
        title = article.get("title", "")

        if "author" in article:
            first_author = article["author"].split(",").pop(0).capitalize()
            dir_ = first_author[0]
            path = f"{first_author}{year}_{title}"
        else:
            dir_ = "Unknown"
            path = f"{year}_{title}"

        # replace spaces with underscores and ensure that string is a valid filepath
        # adapted from: https://github.com/django/django/blob/main/django/utils/text.py
        path = str(path).strip().replace(" ", "_")
        path = path.replace("\n", "_")
        path = re.sub(r"(?u)[^-\w.]", "", path)

        # add sub-directory prefix
        path = os.path.join(dir_, path)

        # add file extension
        path = path + ".md"

        # add suffix if an article already exists with the same path
        cursor.execute(f"SELECT COUNT(id) FROM articles WHERE note='{path}';")
        num_matches = cursor.fetchall()[0][0]

        i = 0

        while num_matches > 0:
            alt_path = re.sub(r"\.md$", string.ascii_lowercase[i] + ".md", path)

            cursor.execute(f"SELECT COUNT(id) FROM articles WHERE note='{alt_path}';")
            num_matches = cursor.fetchall()[0][0]

            if num_matches == 0:
                path = alt_path

        return path
