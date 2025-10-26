from pkg.math_utils import sign_bucket

def test_positive():
    assert sign_bucket(5) == 1

def test_zero():
    assert sign_bucket(0) == 0
