import time
import pytest
import threading
import random
import web

from .. import cache
from ...mocks import mock_memcache

class TestMemoizedFunction:
    def setup_method(self, method):
        self.calls = 0
        
        def square(x): 
            self.calls += 1
            return x * x

        self.cache = cache.MemoryCache()
        keyfunc = lambda x: "sqr-%d" % x
        self.f = cache.MemoizedFunction(square, cache=self.cache, keyfunc=keyfunc)
    
    def test_cached(self):
        """If the value is already cached, the function should not be called."""
        self.f(2)
        assert self.f(2) == 4
        assert self.calls == 1

    def test_notcached(self):
        """When the value is not already cached, the function should be called and cache must get updated."""
        
        assert self.f(2) == 4
        self.calls == 1
        assert self.cache.get('sqr-2') is not None
    
class BaseTestCache:
    def test_getset(self):
        assert self.cache.get("foo") is None
        self.cache.set("foo", 1)
        assert self.cache.get("foo") == 1
        
    def test_add(self):
        assert self.cache.add("foo", 1) is True
        assert self.cache.add("foo", 2) is False
        assert self.cache.get("foo") == 1
        
    def test_delete(self):
        self.cache.set("foo", 1)
        assert self.cache.delete("foo") is True
        assert self.cache.delete("foo") is False

        assert self.cache.delete("bar") is False
        
class TestMemoryCache(BaseTestCache):
    def setup_method(self, method):
        self.cache = cache.MemoryCache()
        
class TestRequestCache(BaseTestCache):
    def setup_method(self, method):
        web.ctx.clear()
        self.cache = cache.RequestCache()

    def test_with_threads(self):
        self.failures = 0
                  
        def f(x):
            if cache.get("foo") != None:
                self.failures += 1
            time.sleep(random.randint(1, 4) / 10.0)
            cache.set("foo", x)
            if cache.get("foo") != x:
                self.failures += 1
        
        threads = [threading.Thread(target=f, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert self.failures == 0
        
class Test_memoize:
    def memoized_square(self, **kwargs):
        self.calls = 0
        
        @cache.memoize(**kwargs)
        def square(x):
            self.calls += 1
            return x*x
        return square

    def test_simple(self):
        square = self.memoized_square()

        assert square(4) == 16
        assert self.calls == 1

        assert square(4) == 16
        assert self.calls == 1
        
    def test_cacheable(self):
        def cacheable(key, value):
            return value > 100
        square = self.memoized_square(cacheable=cacheable) 

        # large values are cached
        square(50)
        square(50)
        assert self.calls == 1
        
        # small values are not cached
        self.calls = 0
        square(5)
        square(5)
        assert self.calls == 2

def test_PrefixKeyFunc():
    f = cache.PrefixKeyFunc("foo")
    assert f() == 'foo-'
    assert f(1) == 'foo-1'
    assert f("x") == 'foo-"x"'
    assert f(1, "x") == 'foo-1,"x"'
    assert f(1, "x", offset=10, limit=10) == 'foo-1,"x"-{"limit":10,"offset":10}'
    
def test_make_key_funn():
    def square(x): return x*x
    
    # When prefix is None, it should create a PrefixKeyFunc
    keyfunc = cache._make_key_func(None, square)
    assert isinstance(keyfunc, cache.PrefixKeyFunc)
    assert keyfunc.prefix == "openlibrary.core.tests.test_cache.square"
    assert keyfunc(1) == "openlibrary.core.tests.test_cache.square-1"

    # When a prefix is specified, it should create a PrefixKeyFunc with that prefix
    keyfunc = cache._make_key_func("square", square)
    assert isinstance(keyfunc, cache.PrefixKeyFunc)
    assert keyfunc.prefix == "square"
    assert keyfunc(1) == "square-1"

    # when a function is specified that should be used
    def f(x): return "sqr-%d" % x
    keyfunc = cache._make_key_func(f, square)
    assert keyfunc is f
