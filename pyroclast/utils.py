def listify(x):  # pragma: no cover
    if x is None:
        return []
    elif isinstance(x, list):
        return x
    else:
        return [x]
