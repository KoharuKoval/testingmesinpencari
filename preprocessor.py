import re
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory


class IndonesianPreprocessor:
    def __init__(self):
        stem_factory = StemmerFactory()
        self.stemmer = stem_factory.create_stemmer()

        stop_factory = StopWordRemoverFactory()
        self.stopwords = set(stop_factory.get_stop_words())
        self.stopwords.update({
            "baca", "juga", "simak", "berikut", "adalah", "yaitu", "yakni",
            "dalam", "untuk", "pada", "dengan", "yang", "dari", "akan", "bisa",
            "dapat", "hal", "cara", "tips", "pemula", "artikel", "halaman"
        })
        self.stem_cache = {}

    def stem_word(self, word: str) -> str:
        if word not in self.stem_cache:
            self.stem_cache[word] = self.stemmer.stem(word)
        return self.stem_cache[word]

    def preprocess(self, text: str) -> list[str]:
        """Pipeline: Case Folding -> Cleaning -> Tokenizing -> Stopword Removal -> Stemming."""
        text = text.lower()
        text = re.sub(r"http\S+|www\S+", " ", text)
        text = re.sub(r"[^a-z\s]", " ", text)
        tokens = text.split()

        processed_tokens = []
        for token in tokens:
            if len(token) > 2 and token not in self.stopwords:
                stemmed = self.stem_word(token)
                if len(stemmed) > 2 and stemmed not in self.stopwords:
                    processed_tokens.append(stemmed)

        return processed_tokens