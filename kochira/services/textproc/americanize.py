"""
Passive-aggressive spelling corrector.

Ensures that users are using Freedom English.
"""

import enchant
import re

from textblob import TextBlob
from nltk.corpus import wordnet

from kochira.service import Service, background

us_dic = enchant.Dict("en_US")
gb_dic = enchant.Dict("en_GB")

service = Service(__name__, __doc__)

DISSIMILARITY_THRESHOLD = 1


def dissimilarity(gb, us):
    gb_syn = set(wordnet.synsets(gb))
    us_syn = set(wordnet.synsets(us))

    # we don't actually know anything about this word in en_GB, so anything we
    # get back is going to be hella wrong
    if not gb_syn:
        return float("inf")

    return len(gb_syn - us_syn)


def compute_replacements(message):
    blob = TextBlob(message)
    replacements = {}

    for word in blob.words:
        word = str(word)

        if (gb_dic.check(word) or any(word.lower() == s.lower() for s in gb_dic.suggest(word))) and \
            not (us_dic.check(word) or any(word.lower() == s.lower() for s in us_dic.suggest(word))):
            suggestions = sorted([(dissimilarity(word, s), i, s) for i, s in enumerate(us_dic.suggest(word))
                                  if s.lower() != word.lower()])

            if suggestions:
                score, _, replacement = suggestions[0]
                if score <= DISSIMILARITY_THRESHOLD:
                    replacements[word] = replacement

    return replacements


@service.hook("channel_message")
@background
def murrika(client, target, origin, message):
    replacements = compute_replacements(message)

    if not replacements:
        return

    for src, tgt in replacements.items():
        message = re.sub(r"\b{}\b".format(re.escape(src)),
                         "\x1f" + tgt + "\x1f", message)

    client.message(target, "<{origin}> {message}".format(
        origin=origin,
        message=message
    ))
