from .. import isbn

def test_isbn_13_to_isbn_10():
    assert isbn.isbn_13_to_isbn_10("978-0-940787-08-7") == "0940787083"
    assert isbn.isbn_13_to_isbn_10("9780940787087") == "0940787083"
    assert isbn.isbn_13_to_isbn_10("BAD-ISBN") is None
    
def test_isbn_10_to_isbn_13():
    assert isbn.isbn_10_to_isbn_13("0-940787-08-3") == "9780940787087"
    assert isbn.isbn_10_to_isbn_13("0940787083") == "9780940787087"
    assert isbn.isbn_10_to_isbn_13("BAD-ISBN") is None

def test_to10():
    assert isbn.to10(None) is None
    assert isbn.to10("bad-isbn") is None
    assert isbn.to10("0385534639") == "0385534639"
    assert isbn.to10("0-3855-3463-9") == "0385534639"
    assert isbn.to10("9780385534635") == "0385534639"
    assert isbn.to10("978-0385534635") == "0385534639"

def test_to13():
    assert isbn.to13(None) is None
    assert isbn.to13("bad-isbn") is None
    assert isbn.to13("0385534639") == "9780385534635"
    assert isbn.to13("0-3855-3463-9") == "9780385534635"
    assert isbn.to13("9780385534635") == "9780385534635"
    assert isbn.to13("978-0385534635") == "9780385534635"
    