lit-walk
========

**Status (Jan 2022)**: Early development & testing.

Overview
--------

_A random walk across the science literature.._

The purpose of this tool, is help one explore their literature collection in a
stochastic _breadth-first_ manner.

The motivation is help reduce the energy cost associated with deciding exactly _what_
one should read, and to encourage exploration of topics outside of the graviational
wells of the topics we are already most familiar with.

At present, `lit-walk` only uses one's existing bibliography to select articles.
In the future, this is likely to change.

This is _not_ meant to replace a more traditional thorough reading of the literature. At
some point, if you want to understand the subject deeply, deeper and more focused
reading is necessary.

Instead, this can be a fun relatively low-effort way to challenge your basic
understanding on a wider range of topics, and to expose yourself to a variety of ways of
thinking about things and approaching problems.

To get the most out of such an approach, a systematic approach to note-taking is
likely to help.

[Gollum](https://github.com/gollum/gollum) is a free & open-source markdown wiki that is
easy to configure and works great as a personal knowledgebase.

Installation
------------

To instead `lit-walk`, clone this github repo and use `pip` to install it:

```
git clone https://github.com/khughitt/lit-walk
cd lit walk
pip install --user .
```

Configuration
-------------

`lit-walk` looks for a configuration file in `$XDG_CONFIG_HOME` on linux (this is
usually `~/.config`), and `$HOME/.lit-walk` otherwise.

At present, `lit-walk` has only been tested on Linux.

The first time you run `lit-walk`, if no configuration file is found in the above
locations, a default one will be created for there.

See the comments in the generated configuration file for an explanation of what each of
the settings relates to.

Usage
-----

To get started, use your reference manager software, or other means, to generate a
[BibTeX](http://www.bibtex.org/) dump of your library, including all articles that you
want `lit-walk` to draw from.

Next, call `lit-walk add`, and point it to the location where you saved your `.bib`
file:

```
lit-walk add path/to/refs.bib
```

`lit-walk` will parse the bibliography, and generate a sqlite database with the relevant
fields.

To check the status of `lit-walk` database and see how many articles it contains, use
the `info` command:

```
lit-walk info
```

To have `lit-walk` suggest an article, simply call:

```
lit-walk walk
```

`lit-walk` will randomly select an article from your collection, and print the article
_title_, _authors_, _abstract_, _year_, _doi_, and _url_.

Additionally, an entry will be recorded in the `stats` table of `lit-walk` database. In
the future, this will be changed so that the user can decide whether to count the
article in their stats, or not.

Future Plans
------------

1. [ ] Use topic modeling or NER to detect informative terms and use this to infer a
   _topic network_.
2. [ ] Modify article selection behavior so that it actually performs a random walk
   across the network, with a parameter to control the average distance travelled (at
   present, articles are randomly sampled with equal probability)
3. [ ] Add option to adjust article weights based on node _degree_ and _betweeness
   centrality_ in an article network.
  - decreasing the priority for articles that are part of large clusters can help to
    avoid picking too many things you are already more likely to be familiar with.
  - on the flip side, one may also want to decrease the odds of choosing articles that
    are completely removed from what the user knows, and thus, may cover topics for
    which the user has _little context_ from which to understand its contents.
  - instead, articles which are not in dead center of highly-connected hubs, and which
    also are in the direction of some smaller, less-frequented communities of articles
    may be good candidates since are likely to both provide some familiar context to
    connect ones understanding to, but also include some less famililar ideas as well.
  - finally, _betweeness centrality_ may be useful to increase the priority for
    articles which form "bridges", connecting to large, but mostly unconnected
    communities in ones collection.
4. [ ] Basic markdown note-talking support
  - provide user with option to open an editor for the suggested article, or, for one or
    more of the topics it covers, in order to take notes as they are reading it.
  - integration with external knowledgebases / note-taking tools.
5. [ ] Infer "empirical" / "global" networks from Pubmed, arxiv, etc.
  - provide support for generate topic networks from the users article collection,
    arxiv/pubmed, and the user's notes.
  - differences between these networks can be used for things like article suggestion /
    infering blindspots, and for getting a sense of the difference between the topics
    covered in ones article collection, ones notes, and the entirety of the science
    literature, or some useful subset of it.

Development
-----------

`lit-walk` is still in the early stages of development and testing, and is likely to
change significantly in the coming months.

One of the main goals of `lit-walk` is to develop a useful approach to _embedding_
articles, in order to assess their similarity and detect communities of related
articles, and also to infer a _topic network_ corresponding to the topics covered in a
users collection.

In order to make it simpler to explore alternative approaches to generating such
embeddings, a `data` command is also provided, which is able to output various datasets
generated from ones collection as [data packages](https://specs.frictionlessdata.io/data-package/).

To see a list of data types that may be generated, run:

```
lit-walk data
```

Notes
-----

If `tokenization.lemmatize` is set to `true` in your configuration, then the
[Stanza NLP Package](https://stanfordnlp.github.io/stanza/) will be used to lemmatize
the text, prior to tokenization and additional processing.

If you have not used Stanza before, the first time it is called, [English Language
models](https://stanfordnlp.github.io/stanza/available_models.html) will need to be
downloaded, which may take some time. This will only take place upon the first call,
however, and the cached language models will be re-used in subsequent calls.

At present, only Paperpile .bib exports have been tested, and modficiations will likely
be needed to support other formats
