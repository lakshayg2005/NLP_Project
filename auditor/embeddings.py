
"""Sentence-embedding semantic similarity against the risk phrase bank."""

from functools import lru_cache

from auditor.config import get_settings
from auditor.lexicon import PHRASE_BANK, _is_safe_pricing_context
from auditor.text_utils import split_sentences


@lru_cache
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(get_settings().embedding_model)


@lru_cache
def _bank_embeddings():
    model = _model()
    return {
        category: model.encode(
            phrases,
            convert_to_tensor=True,
            normalize_embeddings=True,
        )
        for category, phrases in PHRASE_BANK.items()
    }


def semantic_scores(text: str) -> dict[str, dict]:
    """Calculate semantic similarity using sentences that are not explicitly safe pricing statements."""
    from sentence_transformers import util

    sentences = split_sentences(text) or [(0, len(text), text)]

    candidate_sentences = [
        sentence
        for sentence in sentences
        if not _is_safe_pricing_context(text, sentence[0], sentence[1])
    ]

    if not candidate_sentences:
        start, end, sentence = sentences[0]

        return {
            category: {
                "score": 0.0,
                "sentence": sentence,
                "start": start,
                "end": end,
            }
            for category in PHRASE_BANK
        }

    sent_emb = _model().encode(
        [sentence[2] for sentence in candidate_sentences],
        convert_to_tensor=True,
        normalize_embeddings=True,
    )

    results = {}

    for category, bank in _bank_embeddings().items():
        sims = util.cos_sim(sent_emb, bank)
        best_per_sentence = sims.max(dim=1).values
        idx = int(best_per_sentence.argmax())

        start, end, sentence = candidate_sentences[idx]

        results[category] = {
            "score": float(best_per_sentence[idx]),
            "sentence": sentence,
            "start": start,
            "end": end,
        }

    return results
