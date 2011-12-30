from . import OLStore

class TestOLStore:
    def setup_method(self, m):
        self.store = OLStore("sqlite:///:memory:")
        
    def test_get_coverid(self):
        self.store.get_coverid("ISBN:123456789X") == -1
        
        doc = {
            "key": "/books/OL1M",
            "type": {"key": "/type/edition"},
            "isbn_10": ["123456789X"],
            "covers": [12345],
            "last_modified": {
                "type": "/type/datetime",
                "value": "2011-01-02 03:04:05"
            }
        }
        self.store.put(doc['key'], doc)
        self.store.get_coverid("ISBN:123456789X") == 12345