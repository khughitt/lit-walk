"""
NLP-related functionality for lit-walk
"""
import gensim
import stanza

STOP_WORDS = list(gensim.parsing.preprocessing.STOPWORDS)

# extended version of stop words, focused on problematic and ambiguous keyword values..
# _contextual_ words, which describe the nature of the article, as opposed to its
# content, are also excluded.
STOP_WORDS = STOP_WORDS + [
    "of the", "tig", "org", "cin", "geo", "analysis", "mass", "read", 
    "review", "core", "s disease", "r package", "life", "technology",
    "training"
]

def remove_stopwords(txt):
    """
    Uses Stanza's tokenizer to tokenize an input string
    """
    nlp = stanza.Pipeline(lang='en', processors='tokenize')

    doc = nlp(txt)

    sentences = []

    # iterate over input sentences, tokenize, and remove stopwords
    for i, sentence in enumerate(doc.sentences):
        filtered = [] 

        for token in sentence.tokens:
            if token.text not in STOP_WORDS:
                filtered.append(token.text)

        sentences.append(" ".join(filtered))

    #tokenized = list(set(tokenized + tokens))


