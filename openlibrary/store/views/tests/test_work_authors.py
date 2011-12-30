from ..work_authors import WorkAuthorsView

class TestWorkAuthorsView:
    def test_get_author_keys(self):
        f = WorkAuthorsView().get_author_keys

        doc = {
            "key": "/works/OL1W",
            "type": {"key": "/type/work"},
        }
        assert f(doc) == []

        doc = {
            "key": "/works/OL1W",
            "type": {"key": "/type/work"},
            "authors": [{
                "type": {"key": "/type/author_role"},
                "author": {"key": "/authors/OL1A"} 
            }]
        }
        assert f(doc) == ['/authors/OL1A']

        doc = {
            "key": "/works/OL1W",
            "type": {"key": "/type/work"},
            "authors": [{
                "type": {"key": "/type/author_role"},
                "author": {"key": "/authors/OL1A"} 
            }, {
                "type": {"key": "/type/author_role"},
                "author": {"key": "/authors/OL2A"} 
            }]
        }
        assert f(doc) == ["/authors/OL1A", "/authors/OL2A"]

    def test_get_author_keys_with_bad_data(self):
        f = WorkAuthorsView().get_author_keys
        
        doc = {
            "key": "/works/OL1W",
            "type": {"key": "/type/work"},
            "authors": [{
            }]
        }
        assert f(doc) == []
        
        doc = {
            "key": "/works/OL1W",
            "type": {"key": "/type/work"},
            "authors": [{
                "author": {}
            }]
        }
        assert f(doc) == []
        
    def map(self, doc):
        return list(WorkAuthorsView().map(doc))
        
    def test_map_with_no_author(self):
        doc = {
            "key": "/works/OL1W",
            "type": {"key": "/type/work"},
        }
        assert self.map(doc) == []
        
    def test_map_with_single_author(self):
        doc = {
            "key": "/works/OL1W",
            "type": {"key": "/type/work"},
            "authors": [{
                "type": {"key": "/type/author_role"},
                "author": {"key": "/authors/OL1A"} 
            }]
        }
        assert self.map(doc) == [
            {"author_key": "/authors/OL1A"}
        ]

    def test_map_with_two_authors(self):
        doc = {
            "key": "/works/OL1W",
            "type": {"key": "/type/work"},
            "authors": [{
                "type": {"key": "/type/author_role"},
                "author": {"key": "/authors/OL1A"} 
            }, {
                "author": {"key": "/authors/OL2A"} 
            }]
        }
        assert self.map(doc) == [
            {"author_key": "/authors/OL1A"},
            {"author_key": "/authors/OL2A"},
        ]

    def test_map_with_other_types(self):
        doc = {
            "key": "/works/OL1W",
            "type": {"key": "/type/delete"},
            "authors": [{
                "type": {"key": "/type/author_role"},
                "author": {"key": "/authors/OL1A"} 
            }]
        }
        assert self.map(doc) == []
