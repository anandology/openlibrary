"""Caching utilities.
"""
import time
import threading

import memcache
import simplejson
import web

__all__ = [
    "cached_property",
    "Cache", "MemoryCache", "MemcacheCache", "RequestCache",
    "memoize"
]

def cached_property(name, getter):
    """Decorator like `property`, but the value is computed on first call and cached.
    
    class Foo:
        def create_memcache_client(self):
            ...
        memcache_client = cache_property("memcache_client", create_memcache_client)
    """
    def g(self):
        if name in self.__dict__:
            return self.__dict__[name]
            
        value = getter(self)
        self.__dict__[name] = value
        return value
    return property(g)

class Cache(object):
    """Cache interface."""
    def get(self, key):
        """Returns the value for given key. Returns None if that key is not present in the cache.
        """
        raise NotImplementedError()
    
    def set(self, key, value, expires=0):
        """Sets a value in the cache. 
        If expires is non-zero, the cache may delete that entry from the cache after expiry.
        The implementation can choose to ignore the expires argument.
        """
        raise NotImplementedError()
        
    def add(self, key, value, expires=0):
        """Adds a new entry in the cache. Nothing is done if there is already an entry with the same key.
        
        Returns True if a new entry is added to the cache.
        """
        raise NotImplementedError()
        
    def delete(self, key):
        """Deletes an entry from the cache. No error is raised if there is no entry in present in the cache with that key.
        
        Returns True if the key is deleted.
        """
        raise NotImplementedError()


class MemoryCache(Cache):
    """Cache implementation in memory.
    """
    def __init__(self):
        self.d = {}
        
    def get(self, key):
        return self.d.get(key)
        
    def set(self, key, value, expires=0):
        self.d[key] = value
    
    def add(self, key, value, expires=0):
        return self.d.setdefault(key, value) is value
    
    def delete(self, key):
        return self.d.pop(key, None) is not None


class MemcacheCache(Cache):
    """Cache implementation using memcache.
    
    Expects that the memcache servers are specified in web.config.memcache_servers.
    """
    def load_memcache(self):
        servers = web.config.get("memcache_servers", [])
        return memcache.Client(servers)
    
    memcache = cached_property("memcache", load_memcache)
    
    def get(self, key):
        return self.memcache.get(key)
        
    def set(self, key, value, expires=0):
        return self.memcache.set(key, value, expires)
        
    def add(self, key, value, expires=0):
        return self.memcache.add(key, value, expires)
        
    def delete(self, key):
        return self.memcache.delete(key)


class RequestCache(Cache):
    """Request-Local cache.
    
    The values are cached only in the context of the current request.
    """
    def get_d(self):
        return web.ctx.setdefault("request-local-cache", {})
    
    d = property(get_d)

    def get(self, key):
        return self.d.get(key)
        
    def set(self, key, value, expires=0):
        self.d[key] = value
    
    def add(self, key, value, expires=0):
        return self.d.setdefault(key, value) is value
    
    def delete(self, key):
        return self.d.pop(key, None) is not None

    
memory_cache = MemoryCache()
memcache_cache = MemcacheCache()
request_cache = RequestCache()

def _get_cache(engine):
    d = {
        "memory": memory_cache,
        "memcache": memcache_cache,
        "memcache+memory": memcache_cache,
        "request": request_cache
    }
    return d.get(engine)


def memoize(engine="memory", expires=0, background=False, key=None, cacheable=None):
    """Memoize decorator to cache results in various cache engines.
    
    Usage:
        
        @cache.memoize(engine="memcache")
        def some_func(args):
            pass
    
    Arguments:
    
    * engine:
        Engine to store the results. Available options are:
        
            * memory: stores the result in memory.
            * memcache: stores the result in memcached.
            * request: stores the result only in the context of the current request.
    
    * expires:
        The amount of time in seconds the value should be cached. Pass expires=0 to cache indefinitely.
        
    * background:
        Indicates that the value must be recomputed in the background after
        the timeout. Until the new value is ready, the function continue to
        return the same old value.
        
    * key:
        key to be used in the cache. If this is a string, arguments are append
        to it before making the cache-key. If this is a function, it's
        return-value is used as cache-key and this function is called with the
        arguments. If not specified, the default value is computed using the
        function name and module name.
        
    * cacheable:
        Function to determine if the returned value is cacheable. Sometimes it
        is desirable to not cache return values generated due to error
        conditions. The cacheable function is called with (key, value) as
        arguments.
        
    Advanced Usage:
    
    Sometimes, it is desirable to store results of related functions in the
    same cache entry to reduce memory usage. It can be achieved by making the
    ``key`` function return a tuple of two values. (Not Implemented yet)
    
        @cache.memoize(engine="memcache", key=lambda page: (page.key, "history"))
        def get_history(page):
            pass
            
        @cache.memoize(engine="memoize", key=lambda key: (key, "doc"))
        def get_page(key):
            pass
    """
    cache = _get_cache(engine)
    if cache is None:
        raise ValueError("Invalid cache engine: %r" % engine)
        
    def decorator(f):
        keyfunc = _make_key_func(key, f)
        return MemoizedFunction(f, cache, keyfunc, cacheable=cacheable)
    
    return decorator

def _make_key_func(key, f):
    key = key or (f.__module__ + "." + f.__name__)
    if isinstance(key, basestring):
        return PrefixKeyFunc(key)
    else:
        return key
    
class PrefixKeyFunc:
    """A function to generate cache keys using a prefix and arguments.
    """
    def __init__(self, prefix):
        self.prefix = prefix
    
    def __call__(self, *a, **kw):
        return self.prefix + "-" + self.encode_args(a, kw)
        
    def encode_args(self, args, kw={}):
        """Encodes arguments to construct the memcache key.
        """
        # strip [ and ] from key
        a = self.json_encode(list(args))[1:-1] 

        if kw:
            return a + "-" + self.json_encode(kw)
        else:
            return a
    
    def json_encode(self, value):
        """simplejson.dumps without extra spaces and consistant ordering of dictionary keys.

        memcache doesn't like spaces in the key.
        """
        return simplejson.dumps(value, separators=(",", ":"), sort_keys=True)
    
class MemoizedFunction:
    def __init__(self, f, cache, keyfunc, expires=0, background=False, cacheable=None):
        self.f = f
        self.cache = cache
        self.keyfunc = keyfunc
        self.expires = expires
        self.background = background
        self.cacheable = cacheable
        
    def __call__(self, *args, **kwargs):
        key = self.keyfunc(*args, **kwargs)
        value_time = self.cache.get(key)
        
        # value is not found in cache
        if value_time is None:
            value, t = self.update(key, args, kwargs)
        else:
            value, t = value_time
            
            # value is found in cache, but it is expired
            if self.expires and t + self.expires < time.time():
                # update the value
                if self.background:
                    self.update_async(key, args, kwargs)
                else:
                    value, t = self.update(key, args, kwargs)
        return value
        
    def update(self, key, args, kwargs):
        value = self.f(*args, **kwargs)
        t = time.time()

        if self.background:
            # Give more time to compute the value in background after expiry
            expires = 2*self.expires
        else:
            expires = self.expires
        
        if self.cacheable is None or self.cacheable(key, value):
            self.cache.set(key, [value, t], expires)
        return value, t

    def update_async(self, key, args, kwargs):
        """Starts the update process asynchronously.
        """
        t = threading.Thread(target=self._update_async_worker, args=(key, args, kwargs))
        t.start()

    def _update_async_worker(self, key, args, kwargs):
        flag_key = key + "/flag"

        # set a flag to tell indicate that this value is being computed
        if not self.cache.add(flag_key, "true", self.expires):
            # ignore if someone else has already started the compuration
            return

        try:
            self.update(key, args, kwargs)
        finally:
            # remove the flag
            self.cache.delete(flag_key)