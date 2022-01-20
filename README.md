lit-walk
========

**Status (Jan 2022)**: Early development & testing.

Overview
--------

_A random walk across the science literature.._

**Motivation**

1. to help find relevant research
2. to facilitate learning at one's edge
3. to visualize the context surrounding an article or topic

Installation
------------

Install lit-walk and dependencies:

```
pip install -e .
```

Download [Stanza English language model](https://stanfordnlp.github.io/stanza/download_models.html):

```
python -c "import stanza; stanza.download('en')"
```

Usage
-----

```
lit-walk add path/to/refs.bib
lit-walk info
lit-walk walk
lit-walk data [tfidf|cosine|pca|tsne]
```
