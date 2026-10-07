"""path-DAG stable topological sort, indicator naming, SMT-LIB2, PathDagOp."""

from litespec.pathdag.indicator_naming import INDICATOR_NAMING_LITERAL, indicator_for
from litespec.pathdag.path_dag_op_model import derive_path_dag_op
from litespec.pathdag.smt_lib2_serialization import derive_smt2_form, smt2_form_hash
from litespec.pathdag.stable_topological_sort import stable_topological_sort
from litespec.schema.enums import PathNodeKind
from litespec.schema.path_condition_dag import PathConditionDAG, PathNode
from litespec.schema.primitives import Predicate


def _node(node_id, parent=None, expr="true", kind="seq"):
    return PathNode(
        node_id=node_id,
        indicator="",
        parent=parent,
        guard=Predicate(expression=expr, description=""),
        kind=PathNodeKind(kind),
    )


def test_stable_topological_sort_tiebreak():
    # n0(root) -> n2(index 1) and n1(index 2) both ready after n0.
    nodes = [_node("n0", None, kind="entry"), _node("n2", "n0"), _node("n1", "n0")]
    ordered = stable_topological_sort(nodes)
    assert [n.node_id for n in ordered] == ["n0", "n2", "n1"]


def test_stable_topological_sort_parent_before_child():
    nodes = [
        _node("n0", None, kind="entry"),
        _node("n1", "n0"),
        _node("n2", "n0"),
        _node("n3", "n1"),
    ]
    ordered = stable_topological_sort(nodes)
    order = [n.node_id for n in ordered]
    assert order.index("n0") < order.index("n1") < order.index("n3")
    assert order.index("n0") < order.index("n2")


def test_indicator_naming():
    assert indicator_for("search_bounded_dag", 0) == "p_search_bounded_dag_0"
    assert INDICATOR_NAMING_LITERAL == "p_<dag_id>_<i>_by_stable_topological_order"


def test_smt_lib2_form_and_hash():
    dag = PathConditionDAG(
        dag_id="d",
        root="n0",
        nodes=[
            _node("n0", None, kind="entry"),
            _node("n1", "n0", expr="x < 10", kind="loop_body"),
        ],
    )
    body = derive_smt2_form(dag)
    assert "(declare-fun p_d_0 () Bool)" in body
    assert "(assert (=> p_d_1 p_d_0))" in body
    assert "(assert (=> p_d_1 x < 10))" in body
    assert "(assert p_d_0)" in body
    assert smt2_form_hash(dag) == smt2_form_hash(dag)  # deterministic


def test_derive_path_dag_op_assigns_canonical_indicators():
    dag = PathConditionDAG(
        dag_id="d",
        root="n0",
        nodes=[
            _node("n0", None, kind="entry"),
            _node("n1", "n0", kind="seq"),
            _node("n2", "n1", kind="loop_body"),
        ],
    )
    op = derive_path_dag_op(dag)
    assert [n.indicator for n in op.nodes] == ["p_d_0", "p_d_1", "p_d_2"]
    assert op.indicator_naming == INDICATOR_NAMING_LITERAL
    assert len(op.canonical_hash) == 64
    assert op.derived_smt2_hash == smt2_form_hash(dag)
