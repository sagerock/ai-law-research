import re


CASE_CAPTION_STOP_WORDS = {"v", "vs", "versus", "the", "of", "in", "re", "et", "al"}


def case_title_terms(query: str, limit: int = 8) -> list[str]:
    terms = []
    for token in re.findall(r"[a-z0-9]+", query.lower()):
        if len(token) < 2 or token in CASE_CAPTION_STOP_WORDS or token in terms:
            continue
        terms.append(token)
        if len(terms) == limit:
            break
    return terms
