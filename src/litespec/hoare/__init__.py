"""Hoare decomposition (D67, §9.21)."""

from litespec.hoare.hoare_decomposition import HoareDecompositionResult, derive_hoare_decomposition
from litespec.hoare.normal_post import halt_of, normal_post_of
from litespec.hoare.possible_outcomes import possible_outcomes_of_subpart
from litespec.hoare.rule_reference import is_compound_rule, rule_of_command
from litespec.hoare.triple_construction import conclusion_ref, mk_sub, parent_ref, premise_ref, synthetic_node

__all__ = [
    "HoareDecompositionResult",
    "conclusion_ref",
    "derive_hoare_decomposition",
    "halt_of",
    "is_compound_rule",
    "mk_sub",
    "normal_post_of",
    "parent_ref",
    "possible_outcomes_of_subpart",
    "premise_ref",
    "rule_of_command",
    "synthetic_node",
]
