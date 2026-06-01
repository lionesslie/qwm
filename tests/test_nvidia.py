import pytest
from qwm.nvidia.detect import is_nvidia_loaded

def test_is_nvidia_loaded():
    # It might return True or False depending on the host, but shouldn't crash
    result = is_nvidia_loaded()
    assert isinstance(result, bool)
