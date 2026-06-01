def get_current_method_path(clazz, method):
    return f"{clazz.__class__.__module__}.{clazz.__class__.__qualname__}.{method.__name__}"