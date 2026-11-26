"""Cosmic Ray operator provider: exposes the operators as sqe/<Name>."""
from .operators import DropConjunct, StockDeltaOffByOne, WorkflowStatusSwap

_OPS = {op.__name__: op for op in (WorkflowStatusSwap, DropConjunct, StockDeltaOffByOne)}


class Provider:
    def __iter__(self):
        return iter(_OPS)

    def __getitem__(self, name):
        return _OPS[name]
