from .. import common

def test_get_type():
    doc = {
        "key": "/books/OL1M",
        "type": {"key": "/type/edition"}
    }
    assert common.get_type(doc) == "/type/edition"

def test_get_edition_identifiers():
    doc = {
        "key": "/books/OL1M",
        "type": {"key": "/type/edition"}
    }
    assert common.get_edition_identifiers(doc) == {}
    
    doc = {
        "key": "/books/OL1M",
        "type": {"key": "/type/edition"},
        "isbn_10": ["123456789X"],
        "ocaid": "foo00bar",
        "lccn": ["5501234"],
        "identifiers": {
            "goodreads": ["1234"]
        }
    }
    
    assert common.get_edition_identifiers(doc) == {
        "isbn_10": ["123456789X"],
        "ia": ["foo00bar"],
        "lccn": ["5501234"],
        "goodreads": ["1234"]
    }