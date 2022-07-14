"""
NLP-related functionality for lit-walk
"""

# stop words
# source: gensim.parsing.preprocessing.STOPWORDS
STOP_WORDS = ['a', 'about', 'above', 'across', 'after', 'afterwards', 'again',
        'against', 'all', 'almost', 'alone', 'along', 'already', 'also', 'although',
        'always', 'am', 'among', 'amongst', 'amoungst', 'amount', 'an', 'and',
        'another', 'any', 'anyhow', 'anyone', 'anything', 'anyway', 'anywhere', 'are',
        'around', 'as', 'at', 'back', 'be', 'became', 'because', 'become', 'becomes',
        'becoming', 'been', 'before', 'beforehand', 'behind', 'being', 'below',
        'beside', 'besides', 'between', 'beyond', 'bill', 'both', 'bottom', 'but', 'by',
        'call', 'can', 'cannot', 'cant', 'co', 'computer', 'con', 'could', 'couldnt',
        'cry', 'de', 'describe', 'detail', 'did', 'didn', 'do', 'does', 'doesn',
        'doing', 'don', 'done', 'down', 'due', 'during', 'each', 'eg', 'eight',
        'either', 'eleven', 'else', 'elsewhere', 'empty', 'enough', 'etc', 'even',
        'ever', 'every', 'everyone', 'everything', 'everywhere', 'except', 'few',
        'fifteen', 'fifty', 'fill', 'find', 'fire', 'first', 'five', 'for', 'former',
        'formerly', 'forty', 'found', 'four', 'from', 'front', 'full', 'further', 'get',
        'give', 'go', 'had', 'has', 'hasnt', 'have', 'he', 'hence', 'her', 'here',
        'hereafter', 'hereby', 'herein', 'hereupon', 'hers', 'herself', 'him',
        'himself', 'his', 'how', 'however', 'hundred', 'i', 'ie', 'if', 'in', 'inc',
        'indeed', 'interest', 'into', 'is', 'it', 'its', 'itself', 'just', 'keep', 'kg',
        'km', 'last', 'latter', 'latterly', 'least', 'less', 'ltd', 'made', 'make',
        'many', 'may', 'me', 'meanwhile', 'might', 'mill', 'mine', 'more', 'moreover',
        'most', 'mostly', 'move', 'much', 'must', 'my', 'myself', 'name', 'namely',
        'neither', 'never', 'nevertheless', 'next', 'nine', 'no', 'nobody', 'none',
        'noone', 'nor', 'not', 'nothing', 'now', 'nowhere', 'of', 'off', 'often', 'on',
        'once', 'one', 'only', 'onto', 'or', 'other', 'others', 'otherwise', 'our',
        'ours', 'ourselves', 'out', 'over', 'own', 'part', 'per', 'perhaps', 'please',
        'put', 'quite', 'rather', 're', 'really', 'regarding', 'same', 'say', 'see',
        'seem', 'seemed', 'seeming', 'seems', 'serious', 'several', 'she', 'should',
        'show', 'side', 'since', 'sincere', 'six', 'sixty', 'so', 'some', 'somehow',
        'someone', 'something', 'sometime', 'sometimes', 'somewhere', 'still', 'such',
        'system', 'take', 'ten', 'than', 'that', 'the', 'their', 'them', 'themselves',
        'then', 'thence', 'there', 'thereafter', 'thereby', 'therefore', 'therein',
        'thereupon', 'these', 'they', 'thick', 'thin', 'third', 'this', 'those',
        'though', 'three', 'through', 'throughout', 'thru', 'thus', 'to', 'together',
        'too', 'top', 'toward', 'towards', 'twelve', 'twenty', 'two', 'un', 'under',
        'unless', 'until', 'up', 'upon', 'us', 'used', 'using', 'various', 'very',
        'via', 'was', 'we', 'well', 'were', 'what', 'whatever', 'when', 'whence',
        'whenever', 'where', 'whereafter', 'whereas', 'whereby', 'wherein', 'whereupon',
        'wherever', 'whether', 'which', 'while', 'whither', 'who', 'whoever', 'whole',
        'whom', 'whose', 'why', 'will', 'with', 'within', 'without', 'would', 'yet',
        'you', 'your', 'yours', 'yourself', 'yourselves']

class LemmaTokenizer:
    def __init__(self, stopwords, logger, min_length=1, verbose=False):
        import stanza
        from stanza.pipeline.core import ResourcesFileNotFoundError

        try:
            self.nlp = stanza.Pipeline(lang='en', processors='tokenize,pos,lemma',
                                       verbose=verbose)
        except ResourcesFileNotFoundError:
            logger.info("Downloading Stanza English language models for new install..")
            stanza.download('en')

            self.nlp = stanza.Pipeline(lang='en', processors='tokenize,pos,lemma',
                                       verbose=verbose)

        self.min_length = min_length

        # store stopwords in lemmatized form
        self.stopwords = []

        doc = self.nlp(" ".join(stopwords))

        for sent in doc.sentences:
            for word in sent.words:
                self.stopwords.append(word.lemma)

        self.stopwords = set(self.stopwords)

    def __call__(self, text):
        doc = self.nlp(text)
        
        tokens = []

        for sent in doc.sentences:
            for word in sent.words:
                if word.lemma not in self.stopwords and len(word.lemma) >= self.min_length:
                    tokens.append(word.lemma)

        return tokens
