from misc.pyparse.pyparse import is_iterable


def singleton_list_unpacker(result):
    """If `result` is an iterable with len(result) == 1 return only the object"""
    return result[0] if is_iterable(result) and len(result) == 1 else result
