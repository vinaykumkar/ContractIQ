"""Regression test: CUAD gold spans sometimes cut mid-wordpiece-token.

The real case caught by the Phase 2 tiny validation:
gold 'INTELLECTUAL PROPERTY AGREEMENT, d' ends inside the word 'dated'.
Token-level labels must map to the token CONTAINING the cut char (standard
SQuAD behaviour) and the decoded span must contain the gold text, extending at
most to the surrounding token boundaries.
"""
from __future__ import annotations

from ml.src.chunking import tokenize_context
from ml.src.qa_features import answer_token_positions

from conftest import make_clause
from ml.src.chunking import build_windows_for_clause
from ml.src.cuad_loader import AnswerSpan, ClauseQA, ContractRecord


def test_mid_token_gold_span_maps_to_containing_token(tokenizer, small_config):
    # words are 1-char; craft a gold span that cuts the last word in half
    context = "alpha beta gamma delta epsilon zeta"
    # gold ends after the 'd' of 'delta' (char index of 'd' + 1)
    cut = context.index("delta") + 1
    gold = AnswerSpan(text=context[:cut], start=0)
    record = ContractRecord(
        contract_id="MIDTOKEN",
        context=context,
        qas=[ClauseQA(clause_label="test_clause", cuad_category="Test Category",
                      question=make_clause().question, answers=[gold],
                      is_impossible=False, qa_id="MIDTOKEN__Test Category_0")],
    )
    tokenized = tokenize_context(tokenizer, record)
    clause = make_clause()
    q_ids = tokenizer(clause.question, add_special_tokens=False)["input_ids"]
    windows = build_windows_for_clause(
        tokenized, q_ids, clause.label, small_config,
        tokenizer.cls_token_id, tokenizer.sep_token_id,
    )
    hits = [answer_token_positions(w, gold) for w in windows]
    hits = [p for p in hits if p is not None]
    assert hits, "span must map in at least one window"
    # for the window(s) containing the span: decoded chars must CONTAIN gold
    for w in windows:
        pos = answer_token_positions(w, gold)
        if pos is None:
            continue
        local_s = pos[0] - w.ctx_first_token_index_in_window
        local_e = pos[1] - w.ctx_first_token_index_in_window
        char_s = w.ctx_offsets[local_s][0]
        char_e = w.ctx_offsets[local_e][1]
        decoded = context[char_s:char_e]
        assert decoded.startswith(gold.text) or gold.text in decoded
        # the extension beyond the gold span stays within the boundary token
        assert char_e - gold.end <= len("delta")  # at most the rest of the cut word
