"""Effect-expression placeholder at the schema (wire) level.

At the wire level an ``EffectExpr`` is a verbatim string; the structured, frozen
AST lives in :mod:`litespec.lir.effect_expr_ast` and is produced by
:mod:`litespec.lir.parser`.
"""

EffectExpr = str

__all__ = ["EffectExpr"]
