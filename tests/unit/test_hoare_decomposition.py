"""D67 Hoare decomposition of the desugared §18.1 effect."""

from litespec.derivation.for_c_desugaring import desugar_for_c_in
from litespec.hoare import derive_hoare_decomposition
from litespec.lir.parser import parse_effect

_EFFECT = """\
for progress:Nat = 0; progress < limit; progress' = progress + 1 do
  cursor' = advance_cursor(cursor)
od
"""


def test_d67_decomposes_for_c_desugar():
    effect = parse_effect(_EFFECT)
    desugared = desugar_for_c_in(effect)
    result = derive_hoare_decomposition(desugared, "LOS_MemSearchBounded")

    by_name = {sp.name: sp for sp in result.sub_parts}

    # §18.1: seven path-qualified sub-parts.
    assert [sp.name for sp in result.sub_parts] == [
        "seq_part_1",
        "seq_part_2",
        "seq_part_2::while_header",
        "seq_part_2::while_body",
        "seq_part_2::while_body::seq_seg_1",
        "seq_part_2::while_body::seq_seg_2",
        "seq_part_2::while_exit",
    ]
    assert [str(sp.kind) for sp in result.sub_parts] == [
        "seq_segment",
        "seq_segment",
        "while_header",
        "while_body",
        "seq_segment",
        "seq_segment",
        "while_exit",
    ]

    # Head-rule discipline (Rule R181).
    assert str(by_name["seq_part_1"].hoare_triple.rule.rule) == "assign"
    assert str(by_name["seq_part_2"].hoare_triple.rule.rule) == "while"
    assert str(by_name["seq_part_2::while_header"].hoare_triple.rule.rule) == "skip"
    assert str(by_name["seq_part_2::while_body"].hoare_triple.rule.rule) == "seq"
    assert str(by_name["seq_part_2::while_body::seq_seg_1"].hoare_triple.rule.rule) == "assign"
    assert str(by_name["seq_part_2::while_body::seq_seg_2"].hoare_triple.rule.rule) == "assign"
    assert str(by_name["seq_part_2::while_exit"].hoare_triple.rule.rule) == "skip"

    # Premise refs (Rule R150 / actual_premises).
    assert [r.sub_part for r in by_name["seq_part_2"].hoare_triple.rule.premise_refs] == ["seq_part_2::while_body"]
    assert [r.sub_part for r in by_name["seq_part_2::while_body"].hoare_triple.rule.premise_refs] == [
        "seq_part_2::while_body::seq_seg_1",
        "seq_part_2::while_body::seq_seg_2",
    ]

    # Head-role discipline (Rule 0.6x): every conclusion_ref is role "conclusion".
    for sp in result.sub_parts:
        assert str(sp.hoare_triple.rule.conclusion_ref.role) == "conclusion"
        assert sp.hoare_triple.rule.conclusion_ref.sub_part == sp.name

    # Parent triple.
    assert str(result.parent_triple.rule.rule) == "seq"
    assert [r.sub_part for r in result.parent_triple.rule.premise_refs] == ["seq_part_1", "seq_part_2"]
    assert str(result.parent_triple.rule.conclusion_ref.role) == "parent"
    assert result.parent_triple.rule.intermediate_ref.ref == "R_seq_part_1_done"

    # Interface checks: one per sequence boundary.
    ic_ids = {ic.id for ic in result.interface_checks}
    assert ic_ids == {
        "seq_part_1__seq_part_2",
        "seq_part_2::while_body::seq_seg_1__seq_part_2::while_body::seq_seg_2",
    }

    # Control flow is uniformly "normal" (no early return/break/continue).
    for sp in result.sub_parts:
        assert [str(m) for m in sp.hoare_triple.control_flow.members] == ["normal"]


def test_d67_control_flow_return():
    from litespec.lir.effect_expr_ast import Assign, IntLit, Return, Sequence, Var

    effect = Sequence((Assign("x", IntLit(1)), Return(Var("x"))))
    result = derive_hoare_decomposition(effect, "f")
    by_name = {sp.name: sp for sp in result.sub_parts}
    # The return segment has "returning" in its possible outcomes.
    seg2 = by_name["seq_part_2"]
    outcomes = {str(m) for m in seg2.hoare_triple.control_flow.members}
    assert outcomes == {"returning"}
