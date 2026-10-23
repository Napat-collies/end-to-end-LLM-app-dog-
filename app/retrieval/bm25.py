"""A small BM25 keyword retriever - the BASELINE we compare dense retrieval against.

Implemented by hand (about 40 lines) so it is easy to explain in the demo.
Note: it splits on word characters, so a Thai question shares no tokens with
English articles - an expected, measured weakness of keyword search.
"""
import math
import re
from collections import Counter

TOKEN = re.compile(r"\w+", re.UNICODE)
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "was", "for", "on", "with",
    "as", "by", "it", "its", "that", "this", "be", "at", "from", "do", "does", "how", "what",
    "which", "who", "why", "can", "i", "my", "me", "you", "they", "their",
}


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if t not in STOPWORDS]


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tfs = [Counter(tokenize(d)) for d in docs]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avg_len = (sum(self.lens) / len(self.lens)) if self.lens else 0.0
        df = Counter(term for tf in self.tfs for term in tf)
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: str) -> list[float]:
        terms = tokenize(query)
        out = []
        for tf, length in zip(self.tfs, self.lens):
            s = 0.0
            for t in terms:
                if t in tf:
                    f = tf[t]
                    denom = f + self.k1 * (1 - self.b + self.b * length / (self.avg_len or 1))
                    s += self.idf[t] * f * (self.k1 + 1) / denom
            out.append(s)
        return out
