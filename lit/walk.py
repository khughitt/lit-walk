"""
LitWalk Class definition
"""
import re
import random
import os
import yaml
import logging
import sqlite3
import sys
import datetime
import bibtexparser
import pandas as pd
from lit.nlp import STOP_WORDS
from bibtexparser.bparser import BibTexParser
from sklearn.decomposition import PCA
from rich import print

class LitWalk:
    def __init__(self, verbose):
        """Initializes a new LitWalk instance."""
        # setting logging
        self._setup_logger(verbose)

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

    def _setup_logger(self, verbose):
        """Sets up logger to print messages to STDOUT"""
        logging.basicConfig(stream=sys.stdout, 
                            format='[%(levelname)s] %(message)s')

        self._logger = logging.getLogger('lit')

        if verbose:
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.WARN)

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
            
        if "articleTopics" not in tables:
            self._create_article_topics_table(cursor)

        cursor.close()

    #  def detect_keywords(self, articles):
    #      """
    #      Detects & quantifies potential keywords using article titles/abstracts
    #
    #      Limitation: restricted to single word keywords?..
    #      """
    #      pass

    def _update_keywords(self, articles):
        """
        Updates and extends keywords associated with each article using _existing_
        keywords as a guide..

        First, a list of all keywords associated with at least one article is
        inferred.

        Next, the title/abstract of each article is scanned, and any detected keywords which are not already prese

        TODO:
        - [ ] extend keywords for articles that already have some
        - [ ] detect new keywords in titles/abstracts?
        - [ ] stem/lemmatize prior to matching
        - [ ] decide on appropriate way to choose keywords to check against..
        """
        # get a list of keywords of interest
        target_keywords = self._get_target_keywords(articles)

        cur = self.db.cursor()

        for article in articles:
            if article['keywords'] is None:
                new_keywords = []

                for keyword in target_keywords:
                    if (keyword in article['title'].lower() or
                        (article['abstract'] is not None and keyword in
                         article['abstract'].lower())):
                        new_keywords.append(keyword)

                if len(new_keywords) > 0:
                    self._logger.info(f"Adding {len(new_keywords)} new keywords..")

                    # update db
                    res = cur.execute("UPDATE articles SET keywords = ? WHERE doi = ?;",
                                      ("; ".join(new_keywords), article["doi"]))

        self.db.commit()

    def _get_target_keywords(self, articles):
        """
        Returns a list of keywords of sufficient length and frequency
        """
        all_keywords = []

        for article in articles:
            if article['keywords'] is not None:
                keywords = [x.strip() for x in article['keywords'].split(";")]

                all_keywords = all_keywords + keywords

        # for articles with missing keywords, check for common keywords in the
        # title/abstract
        keyword_counts = pd.Series(all_keywords).value_counts()

        # for now, exclude keywords which only appear a small number of times
        min_freq = self._config['keywords']['min_freq']
        min_size = self._config['keywords']['min_size']

        keywords = keyword_counts[keyword_counts >= min_freq].index
        keywords = sorted([x for x in keywords if len(x) >= min_size])

        return keywords

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
            doi text,
            date timestamp
        );
        """
        self._logger.info("Creating stats table...")

        try:
            cursor.execute(sql)
        except sqlite3.Error as e:
            print(e)

    def _create_article_topics_table(self, cursor):
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


    #  def _create_topics_table(self, cursor):
    #      """
    #      Table mapping from specific topics to their place in a topic embedding matrix;
    #      each entry effectively represents a row in the embedding matrix.
    #      """
    #      sql = """
    #      CREATE TABLE IF NOT EXISTS topics (
    #          topic text,
    #          num_articles integer,
    #          times_reviewed integer
    #      );
    #      """
    #      self._logger.info("Creating topics table...")
    #
    #      try:
    #          cursor.execute(sql)
    #      except sqlite3.Error as e:
    #          print(e)

    def _sync(self):
        """
        1. extends article keywords
        2. creates <article x topic> mat?
        """
        articles = self.get_articles()

        # updates keywords based on existing keywords..
        self._update_keywords(articles)

        # testing: perform pca projection on <article x keyword> matrix
        #  df = self.get_keyword_df()

        # exclude articles with no associated keywords..
        #  df = df[df.sum(axis=1) > 0]
        #
        #  pca = PCA(n_components=2, whiten=False, random_state=1)
        #
        #  pca = pca.fit(df.to_numpy())

        # doesn't explain much variance! (~11% / 3%, in testing..)
        # 1. try mca? (prince)
        # 2. heavier filtering of low-freq terms?
        # for now, save data so that it can be experimented with externally..
        #pca.explained_variance_ratio_

        #  pca_df = pd.DataFrame(pca.transform(df.to_numpy()), index=df.index,
        #          columns=['PC1', 'PC2'])

        #  df.to_csv("dat.csv")
        #  pca_df.to_csv("dat_pca.csv")
        #
        #  breakpoint()

    def get_keyword_df(self):
        """Returns an <article, keyword> dataframe"""
        # get up-to-date article entries
        cur = self.db.cursor()
        res = cur.execute("SELECT doi, keywords FROM articles ORDER BY doi;")
        articles = cur.fetchall()

        # convert to list of dicts
        article_dicts = []

        for article in articles:
            article_dicts.append({"doi": article[0], "keywords": article[1]})

        target_keywords = pd.Series(self._get_target_keywords(article_dicts))

        # use a list of rows to build matrix
        rows = []
        dois = []

        # convert keywords to list, and get list of all keywords
        for i, article in enumerate(article_dicts):
            keywords = []

            if article['keywords'] is not None:
                keywords = [x.strip() for x in article['keywords'].split('; ')]

            dois.append(article['doi'])
            rows.append(target_keywords.isin(keywords))

        # combine rows into dataframe
        dat = pd.DataFrame.from_records(rows)
        dat.columns = target_keywords
        dat.index = dois

        # convert to ndarray and return
        dat.replace({False: 0, True: 1}, inplace=True)
        
        return dat

    def get_articles(self, n=None, missing_abstracts=False):
        """Retrieves articles table"""
        cur = self.db.cursor()

        # all articles
        if n is None:
            if missing_abstracts:
                sql = "SELECT * FROM articles WHERE abstract IS NULL;"
            else:
                sql = "SELECT * FROM articles;"
        else:
            # subset of articles
            if missing_abstracts:
                sql = f"SELECT * FROM articles WHERE id IN (SELECT id FROM articles WHERE abstract IS NULL ORDER BY RANDOM() LIMIT {n})"
            else:
                sql = f"SELECT * FROM articles WHERE id IN (SELECT id FROM articles ORDER BY RANDOM() LIMIT {n})"

        res = cur.execute(sql)

        articles = cur.fetchall()

        colnames = [x[0] for x in res.description]

        article_dicts = []

        for article in articles:
            article_dicts.append(dict(zip(colnames, article)))

        return article_dicts

    def walk(self, search):
        """Chooses an article at random"""

        # if no search constraints specified, choose from all articles
        if search == "":
            res = self.get_random()
        else:
            res = self.get_filtered(search)

        # update stats; for now, assume article was read (later: prompt user..)
        self.update_stats(res['article']["doi"])

        return res 

    def get_filtered(self, search):
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

        res = {
            "article": random.sample(filtered, 1)[0],
            "num_included": num_filtered,
            "num_total": num_articles
        }

        return res

    def get_random(self):
        """
        Gets a single random article from among all articles
        """
        cur = self.db.cursor()

        num_articles = self.num_articles()
        ind = random.randint(1, num_articles)

        res = cur.execute(f"SELECT * FROM articles WHERE id={ind};")
        article = cur.fetchall()[0]
        colnames = [x[0] for x in res.description]
        article = dict(zip(colnames, article))
        cur.close()

        res = {
            "article": article,
            "num_included": num_articles,
            "num_total": num_articles
        }

        return res

    def update_stats(self, doi):
        """Add entry to stats table"""
        cur = self.db.cursor()

        res = cur.execute("INSERT INTO stats(doi, date) VALUES (?, ?);",
                          (doi, datetime.datetime.now()))
        self.db.commit()
        cur.close()

    def get_excluded_keywords(self):
        """Returns a list of phrases to ignore when parsing/inferring keywords"""
        stopwords = self._config['keywords']['exclude'] + STOP_WORDS
        stopwords = [x.lower() for x in stopwords]

        return stopwords

    def import_bibtex(self, infile, skip_check=False):
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

        cur = self.db.cursor()

        # exclude existing articles
        if not skip_check:
            cur.execute("SELECT doi FROM articles;")
            
            existing_dois = [x[0] for x in cur.fetchall()]

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
            stopwords = self.get_excluded_keywords()

            self._logger.info(f"Adding {num_after} new articles..")

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
                        entry[field] = entry[field].replace("\n", " ");

                # extract keywords;
                if entry['keywords'] is not None:
                    keywords = []

                    for keyword in entry['keywords'].split(";"):
                        # for now, store all keywords as lowercase (better for matching
                        # in article abstracts, etc.)
                        keyword = keyword.strip().lower()

                        # exclude keywords that either:
                        # 1. match phrases in stop words list, or,
                        # 2. contain a "/", possibly corresponding to a path in
                        #    paperpile (this can be made optional, in the future..)
                        if keyword not in stopwords and not "/" in keyword:
                            keywords.append(keyword)

                    entry['keywords'] = "; ".join(keywords)

                self.add_article(cur, tuple(entry.values()))
            
            self._logger.info(f"Finished!")

            #  self._sync_articles = self.topics(articles)
            self._sync()

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
            "data_dir": os.path.join(str(os.getenv("HOME")), ".lit"),
            "keywords": {
                # exclude keywords with fewer than N characters
                "min_size": 3,
                # minimum number of occurrences of keyword, for it to be used?
                "min_freq": 3,
                # phrases to exclude when parsing/inferring keywords?
                "exclude": []
            }
        }
