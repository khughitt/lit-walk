"""
Test article import functionality
"""
import json
import os
import tempfile
import pytest
from litwalk import LitWalk

TEST_DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")

@pytest.fixture
def lw():
    """Creates a simple litwalk instance to use for testing"""
    data_dir = tempfile.mkdtemp()
    notes_dir = tempfile.mkdtemp()

    return LitWalk(data_dir, notes_dir)

def test_import_paperpile_bibtex(lw):
    """
    Test basic import of bibtex files exported from paperpile
    """
    json_file = os.path.join(TEST_DATA_DIR, "json", "paperpile.json")
    bib_file = os.path.join(TEST_DATA_DIR, "bib", "paperpile.bib")

    with open(json_file, "rt", encoding="utf-8") as fp:
        expected = json.load(fp)

    lw.import_bibtex(bib_file)
    articles = lw.get_articles()

    assert articles == expected
