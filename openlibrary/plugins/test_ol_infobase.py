import ol_infobase
import simplejson

def test_fix_table_of_contents():
    foo = {
        'level': 0,
        'label': u'',
        'title': u'foo',
        'pagenum': u''
    }
    
    assert ol_infobase.fix_table_of_contents(['foo']) == [foo]
    assert ol_infobase.fix_table_of_contents([{"type": "/type/text", "value": "foo"}]) == [foo]
    assert ol_infobase.fix_table_of_contents([{"title": "foo"}]) == [foo]

    bar = {
        'level': 1,
        'label': u'ix',
        'title': u'bar',
        'pagenum': u'10',
    }
    assert ol_infobase.fix_table_of_contents([bar]) == [bar]

def _process_json(key, d):
    json = ol_infobase.process_json(key, simplejson.dumps(d))
    return simplejson.loads(json)
    
def test_process_json():
    assert _process_json("/books/OL1M", {"key": "/b/OL1M"}) == {"key": "/books/OL1M"}
    assert _process_json("/books/OL1M", {"key": "/books/OL1M"}) == {"key": "/books/OL1M"}

    assert _process_json("/authors/OL1A", {"key": "/a/OL1A"}) == {"key": "/authors/OL1A"}
    assert _process_json("/authors/OL1A", {"key": "/authors/OL1A"}) == {"key": "/authors/OL1A"}

def test_toc_via_process_json():
    foo = {
        'level': 0,
        'label': u'',
        'title': u'foo',
        'pagenum': u''
    }
    
    # with string
    doc = {
        "key": "/books/OL1M",
        "table_of_contents": ["foo"]
    }
    assert _process_json("/books/OL1M", doc) == {
        "key": "/books/OL1M",
        "table_of_contents": [foo]
    }

    # with text
    doc = {
        "key": "/books/OL1M",
        "table_of_contents": [{"type": "/type/text", "value": "foo"}]
    }
    assert _process_json("/books/OL1M", doc) == {
        "key": "/books/OL1M",
        "table_of_contents": [foo]
    }
    
    # with dict
    doc = {
        "key": "/books/OL1M",
        "table_of_contents": [foo]
    }
    assert _process_json("/books/OL1M", doc) == {
        "key": "/books/OL1M",
        "table_of_contents": [foo]
    }
    
    
class TestPermissionEngine:
    def test_is_list(self):
        engine = ol_infobase.PermissionEngine()
        assert engine.is_list("/people/anand") is False
        assert engine.is_list("/people/anand/lists/OL1L") is True
        assert engine.is_list("/people/anand/lists/OL1L/foo") is False
        assert engine.is_list("foo/people/anand/lists/OL1L") is False

    def test_get_list_owner(self):
        engine = ol_infobase.PermissionEngine()
        assert engine.get_list_owner("/people/anand/lists/OL1L") == "/people/anand"
        assert engine.get_list_owner("/people/a-b_c/lists/OL1L") == "/people/a-b_c"
        assert engine.get_list_owner("/books/OL1M") == None

    def test_get_list_writers(self):
        doc = self.make_doc({
            "key": "/people/anand/lists/OL1L",
            "type": {"key": "/type/list"},
        })
        
        engine = ol_infobase.PermissionEngine()
        assert list(engine.get_list_writers(doc)) == ["/people/anand"]

        doc = self.make_doc({
            "key": "/people/anand/lists/OL1L",
            "type": {"key": "/type/list"},
            "collaborators": [
                {"key": "/people/foo"},
                {"key": "/people/bar"},
            ]
        })
        assert list(engine.get_list_writers(doc)) == ["/people/anand", "/people/foo", "/people/bar"]
        
    def make_doc(self, data):
        from infogami.infobase.core import Thing
        return Thing.from_dict(None, data['key'], data)
        
    def make_user(self, key):
        return self.make_doc({
            "key": key, 
            "type": {"key": "/type/user"}
        })
        
    def test_has_permission_to_edit_list(self, monkeypatch):
        doc = self.make_doc({
            "key": "/people/anand/lists/OL1L",
            "type": {"key": "/type/list"},
            "collaborators": [
                {"key": "/people/foo"},
            ]
        })
        
        user_anand = self.make_user("/people/anand")
        user_foo  = self.make_user("/people/foo")
        user_bar  = self.make_user("/people/bar")
        
        def get_thing(key):
            if key == doc.key:
                return doc
        
        engine = ol_infobase.PermissionEngine()
        engine.get_thing = get_thing
        
        assert engine.has_permission_to_edit_list(user_anand, doc.key) is True
        assert engine.has_permission_to_edit_list(user_foo, doc.key) is True
        assert engine.has_permission_to_edit_list(user_bar, doc.key) is False