"""Self-tests for the custom mutation operators: every documented example must mutate exactly as stated."""
import pytest
from cosmic_ray.mutating import MutationVisitor

from sqe_operators.operators import DropConjunct, StockDeltaOffByOne, WorkflowStatusSwap


@pytest.mark.parametrize("op", [WorkflowStatusSwap, DropConjunct, StockDeltaOffByOne])
def test_MUT_operator_examples(op):
    for ex in op.examples():
        out = MutationVisitor.mutate_code(ex.pre_mutation_code, op(), ex.occurrence)
        assert out == ex.post_mutation_code, (op.__name__, ex)


def test_MUT_status_swap_ignores_other_strings():
    assert MutationVisitor.mutate_code("x = 'hello'", WorkflowStatusSwap(), 0) is None


def test_MUT_drop_conjunct_on_real_rule():
    src = "if user.is_hod and self.status == 'pending_hod':\n    pass\n"
    assert MutationVisitor.mutate_code(src, DropConjunct(), 0) == "if self.status == 'pending_hod':\n    pass\n"
    assert MutationVisitor.mutate_code(src, DropConjunct(), 1) == "if user.is_hod:\n    pass\n"


def test_MUT_stock_delta_on_real_rule():
    src = "item.quantity_total -= qty_issued\n"
    assert MutationVisitor.mutate_code(src, StockDeltaOffByOne(), 0) == "item.quantity_total -= (qty_issued + 1)\n"
