from . import OLStore

class TestOLStore:
    def setup_method(self, m):
        self.store = OLStore("sqlite:///:memory:", echo=True)

    def make_edition(self, key, last_modified=None, work_key=None, **kw):
        if work_key:
            kw['works'] = [{"key": work_key}]
        return self.make_doc(key, 
            type="/type/edition", 
            last_modified=last_modified,
            **kw)
        
    def make_doc(self, key, type, last_modified=None, **kw):
        if last_modified is None:
            last_modified = "2010-01-01 00:00:00"
        
        d = {
            "key": key,
            "type": {"key": type},
            "last_modified": {
                "type": "/type/datetime",
                "value": last_modified
            }
        }
        d.update(kw)
        return d
        
    def test_get_coverid(self):
        self.store.get_coverid("ISBN:123456789X") == -1
        
        doc = self.make_edition("/books/OL1M", 
                last_modified="2011-01-02 03:04:05",
                isbn_10=["123456789X"], 
                covers=[12345])
        self.store.put(doc['key'], doc)
        self.store.get_coverid("ISBN:123456789X") == 12345
        self.store.get_coverid("isbn:123456789x") == 12345
        
    def test_get_coverid_with_multiple_matches(self):
        doc1 = self.make_edition("/books/OL1M",
                last_modified="2011-01-02 03:04:05",
                isbn_10=["123456789X"],
                covers=[12345])

        doc2 = self.make_edition("/books/OL2M",
                last_modified="2011-01-02 03:04:06",
                isbn_10=["123456789X"],
                covers=[12346])
    
        doc3 = self.make_edition("/books/OL3M", 
                last_modified="2011-01-02 03:04:07",
                isbn_10=["123456789X"])
                
        for d in [doc1, doc2, doc3]:
            self.store.put(d['key'], d)

        self.store.get_coverid("ISBN:123456789X") == 12346
        
    def test_get_work_info(self):
        work1 = self.make_doc("/works/OL1W", type="/type/work")
        work2 = self.make_doc("/works/OL2W", type="/type/redirect", location="/works/OL1W")
        book1 = self.make_doc("/books/OL1M", 
            type="/type/edition", 
            title="Test Book",
            works=[
                {"key": "/works/OL1W"}
            ]
        )
        
        for doc in [work1, work2, book1]:
            self.store.put(doc['key'], doc)
            
        w = self.store.get_work_info("/works/OL1W")
        assert w is not None
        
        assert [doc['key'] for doc in w['editions']] == ["/books/OL1M"]
        assert [doc['key'] for doc in w['redirects']] == ["/works/OL2W"]
        
        assert w['editions'][0]['title'] == 'Test Book'
        
    def make_work(self, key, author_keys=[], **kw):
        return self.make_doc(key,
                type="/type/work",
                authors=[{"author": {"key": akey}} for akey in author_keys],
                **kw)
        
    def test_top_works(self):
        b1 = self.make_edition("/books/OL1M", work_key="/works/OL1W")
        b2 = self.make_edition("/books/OL2M", work_key="/works/OL1W")
        b3 = self.make_edition("/books/OL3M", work_key="/works/OL2W")
        
        w1 = self.make_work("/works/OL1W", author_keys=["/authors/OL1A"])
        w2 = self.make_work("/works/OL2W", author_keys=["/authors/OL1A"])
        
        a1 = self.make_doc("/authors/OL1A", "/type/author")
        
        for doc in [b1, b2, b3, w1, w2, a1]:
            self.store.put(doc['key'], doc)
                
        assert self.store.get_top_works("/authors/OL1A", limit=1) == [
            {"edition_count": 2, "work_key": "/works/OL1W"}
        ]

        assert self.store.get_top_works("/authors/OL1A", limit=2) == [
            {"edition_count": 2, "work_key": "/works/OL1W"},
            {"edition_count": 1, "work_key": "/works/OL2W"},
        ]