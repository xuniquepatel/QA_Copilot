def sign_bucket(x: int) -> int:
    """Return -1 if x<0, 0 if x==0, 1 if x>0."""
    if x < 0:
        return -1
    elif x == 0:
        return 0
    else:
        return 1
