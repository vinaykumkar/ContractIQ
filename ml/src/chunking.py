"""Token-level sliding-window chunking for long contracts.

Design: each contract's context is tokenized exactly ONCE (without special
tokens, keeping char offsets into the original text). Windows for a clause are
then sliced at token level and assembled as [CLS] q_tokens [SEP] ctx_tokens [SEP].

This is mathematically equivalent to Hugging Face's overflow windowing for
(truncation="only_second") but avoids re-tokenizing the same contract text once
per clause (15x+ waste). Window boundaries are deterministic: the first window
holds `max_ctx_tokens` context tokens; each subsequent window advances by
`doc_stride` tokens until the context is fully covered.

Every window keeps the metadata needed to map predictions back to the original
document: contract_id, clause_label, window index, and per-token character
offsets into the ORIGINAL context string.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import WindowConfig
from .cuad_loader import ContractRecord


class ChunkingError(RuntimeError):
    """Raised when a question/window combination cannot fit the configured budget."""


@dataclass
class TokenizedContext:
    """A contract tokenized once, reusable across all clauses."""

    contract_id: str
    context: str
    token_ids: list[int]
    # char offsets into `context` for each token, same length as token_ids
    offsets: list[tuple[int, int]]


@dataclass
class WindowFeatures:
    """One sliding window for one (contract, clause) pair.

    input_ids layout: [CLS] question [SEP] context_window [SEP]
    (no padding - attention masks are all ones; the collator pads at batch time)
    """

    input_ids: list[int]
    question_token_len: int  # tokens between [CLS] and first [SEP]
    # indices into TokenizedContext.token_ids for the context slice
    ctx_token_start: int
    ctx_token_end: int
    # char offsets for the context slice only (len == ctx_token_end - ctx_token_start)
    ctx_offsets: list[tuple[int, int]]
    # metadata for mapping predictions back to the document
    contract_id: str
    clause_label: str
    window_index: int

    @property
    def ctx_first_token_index_in_window(self) -> int:
        return 1 + self.question_token_len + 1

    def char_range(self) -> tuple[int, int]:
        """Character range of the window's context slice in the original text."""
        return self.ctx_offsets[0][0], self.ctx_offsets[-1][1]


def tokenize_context(tokenizer, record: ContractRecord) -> TokenizedContext:
    enc = tokenizer(record.context, add_special_tokens=False, return_offsets_mapping=True)
    return TokenizedContext(
        contract_id=record.contract_id,
        context=record.context,
        token_ids=list(enc["input_ids"]),
        offsets=[(int(s), int(e)) for s, e in enc["offset_mapping"]],
    )


def validate_window_fit(config: WindowConfig, tokenizer, question: str, clause: str) -> int:
    """Check the question fits the budget with room for context; return q token count.

    The question must NEVER be truncated (contract side is the only truncation
    target), so a question that eats the whole window is a configuration error.
    """
    q_ids = tokenizer(question, add_special_tokens=False)["input_ids"]
    special = 3  # [CLS], [SEP], [SEP]
    if len(q_ids) + special >= config.max_seq_len:
        raise ChunkingError(
            f"Question for clause '{clause}' needs {len(q_ids)} tokens + {special} special "
            f"tokens which does not fit max_seq_len={config.max_seq_len}; the question would "
            f"be truncated. Increase max_seq_len or shorten the question."
        )
    return len(q_ids)


def window_token_ranges(
    n_ctx_tokens: int, max_ctx_tokens: int, doc_stride: int
) -> list[tuple[int, int]]:
    """Token ranges [start, end) of overlapping context windows.

    Mirrors HF overflow semantics: first window covers up to max_ctx_tokens,
    each next window advances by doc_stride, no trailing redundant window.
    """
    if max_ctx_tokens <= doc_stride:
        raise ChunkingError(
            f"max_ctx_tokens ({max_ctx_tokens}) must exceed doc_stride ({doc_stride})"
        )
    if n_ctx_tokens == 0:
        return []
    ranges: list[tuple[int, int]] = []
    start = 0
    while True:
        end = min(start + max_ctx_tokens, n_ctx_tokens)
        ranges.append((start, end))
        if end >= n_ctx_tokens:
            break
        start += max_ctx_tokens - doc_stride
    return ranges


def build_windows_for_clause(
    tokenized: TokenizedContext,
    question_token_ids: list[int],
    clause_label: str,
    config: WindowConfig,
    cls_token_id: int,
    sep_token_id: int,
) -> list[WindowFeatures]:
    """Slice the tokenized context into windows and assemble QA input_ids."""
    return build_windows_for_token_slice(
        tokenized, 0, len(tokenized.token_ids),
        question_token_ids, clause_label, config, cls_token_id, sep_token_id,
    )


def build_windows_for_token_slice(
    tokenized: TokenizedContext,
    slice_start: int,
    slice_end: int,
    question_token_ids: list[int],
    clause_label: str,
    config: WindowConfig,
    cls_token_id: int,
    sep_token_id: int,
    first_window_index: int = 0,
) -> list[WindowFeatures]:
    """Windows over a sub-range of the tokenized context (retrieval regions).

    `slice_start`/`slice_end` delimit the region in TokenizedContext token
    coordinates; window boundaries and metadata stay in the original context
    coordinate system, so decoding maps back to the full document unchanged.
    """
    max_ctx = config.max_seq_len - len(question_token_ids) - 3
    windows = []
    for rel_idx, (s, e) in enumerate(
        window_token_ranges(slice_end - slice_start, max_ctx, config.doc_stride)
    ):
        gs, ge = slice_start + s, slice_start + e
        ctx_ids = tokenized.token_ids[gs:ge]
        ctx_offsets = tokenized.offsets[gs:ge]
        input_ids = [cls_token_id] + list(question_token_ids) + [sep_token_id] + ctx_ids + [sep_token_id]
        windows.append(
            WindowFeatures(
                input_ids=input_ids,
                question_token_len=len(question_token_ids),
                ctx_token_start=gs,
                ctx_token_end=ge,
                ctx_offsets=ctx_offsets,
                contract_id=tokenized.contract_id,
                clause_label=clause_label,
                window_index=first_window_index + rel_idx,
            )
        )
    return windows
