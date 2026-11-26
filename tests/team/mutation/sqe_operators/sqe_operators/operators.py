"""Three business-rule mutation operators (parso syntax-tree based, Cosmic Ray 8 API).

WorkflowStatusSwap (BR-3)   'pending_hod' -> 'authorized', 'authorized' -> 'issued', ...
    Simulates a developer wiring a guard or an assignment to the wrong lifecycle state.
DropConjunct       (BR-2)   `a and b`  ->  `a`   and   `a and b` -> `b`
    Simulates a missing condition in an authority check (role / department / status).
StockDeltaOffByOne (BR-4)   `x -= y`   ->  `x -= (y + 1)`   (also `+=`)
    Simulates an off-by-one in a stock posting.
"""
import parso
import parso.python.tree as tree
from cosmic_ray.operators.operator import Example, Operator

# Each status is replaced by its most "plausible wrong" neighbour in the lifecycle (BR-3).
STATUS_NEIGHBOUR = {
    "pending_hod": "authorized",
    "authorized": "issued",
    "issued": "authorized",
    "sent_back": "pending_hod",
    "rejected": "authorized",
    "draft": "pending_hod",
    "cancelled": "pending_hod",
}


def _literal(leaf):
    return leaf.value[1:-1] if len(leaf.value) >= 2 and leaf.value[0] == leaf.value[-1] and leaf.value[0] in "'\"" else None


class WorkflowStatusSwap(Operator):
    def mutation_positions(self, node):
        if node.type == "string" and _literal(node) in STATUS_NEIGHBOUR:
            yield (node.start_pos, node.end_pos)

    def mutate(self, node, index):
        assert index == 0
        quote = node.value[0]
        node.value = f"{quote}{STATUS_NEIGHBOUR[_literal(node)]}{quote}"
        return node

    @classmethod
    def examples(cls):
        return (
            Example("s == 'pending_hod'", "s == 'authorized'"),
            Example('status = "authorized"', 'status = "issued"'),
            Example("s = 'issued'", "s = 'authorized'"),
        )


class DropConjunct(Operator):
    """For an `and` chain with N operands, produce N mutants, each dropping one operand."""

    def _operands(self, node):
        return [c for c in node.children if not (isinstance(c, tree.Keyword) and c.value == "and")]

    def mutation_positions(self, node):
        if node.type == "and_test":
            for _ in self._operands(node):
                yield (node.start_pos, node.end_pos)

    def mutate(self, node, index):
        ops = self._operands(node)
        kept = [o.get_code().strip() for i, o in enumerate(ops) if i != index]
        code = " and ".join(kept)
        prefix = node.get_first_leaf().prefix
        new = parso.parse(code).children[0]
        new = new.children[0] if new.type == "simple_stmt" else new
        new.get_first_leaf().prefix = prefix
        return new

    @classmethod
    def examples(cls):
        return (
            Example("ok = a and b", "ok = b", occurrence=0),
            Example("ok = a and b", "ok = a", occurrence=1),
            Example("if a and b and c: pass", "if a and c: pass", occurrence=1),
        )


class StockDeltaOffByOne(Operator):
    def mutation_positions(self, node):
        if node.type == "expr_stmt" and len(node.children) == 3 and \
                getattr(node.children[1], "value", None) in ("-=", "+="):
            yield (node.start_pos, node.end_pos)

    def mutate(self, node, index):
        assert index == 0
        rhs = node.children[2]
        new_rhs = parso.parse(f"({rhs.get_code().strip()} + 1)").children[0]
        new_rhs = new_rhs.children[0] if new_rhs.type == "simple_stmt" else new_rhs
        new_rhs.get_first_leaf().prefix = rhs.get_first_leaf().prefix
        node.children[2] = new_rhs
        new_rhs.parent = node
        return node

    @classmethod
    def examples(cls):
        return (
            Example("stock -= qty", "stock -= (qty + 1)"),
            Example("total += n", "total += (n + 1)"),
        )
