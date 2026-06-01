import pytest
from qwm.layout.tiling import BSPNode, BSPTilingEngine

def test_bsp_node():
    node = BSPNode(xid=10)
    assert node.xid == 10
    assert node.split_ratio == 0.5

def test_bsp_engine():
    engine = BSPTilingEngine()
    engine.add_window(10)
    assert engine.root is not None
    assert engine.root.xid == 10
