from functools import wraps

def model_cache(field):
    def decorator(f):
        @wraps(f)
        def wrapper(self, save=True, force=False):
            cached_val = getattr(self, field, None)
            if force or cached_val is None:
                cached_val = f(self)
                setattr(self, field, cached_val)
                if save:
                    self.save()
            return cached_val
        return wrapper
    return decorator
