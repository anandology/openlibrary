def check_digit_10(isbn):
    assert len(isbn) == 9
    sum = 0
    for i in range(len(isbn)):
        c = int(isbn[i])
        w = i + 1
        sum += w * c
    r = sum % 11
    if r == 10:
        return 'X'
    else:
        return str(r)

def check_digit_13(isbn):
    assert len(isbn) == 12
    sum = 0
    for i in range(len(isbn)):
        c = int(isbn[i])
        if i % 2: w = 3
        else: w = 1
        sum += w * c
    r = 10 - (sum % 10)
    if r == 10:
        return '0'
    else:
        return str(r)

def isbn_13_to_isbn_10(isbn_13):
    isbn_13 = isbn_13.replace('-', '')
    try:
        assert len(isbn_13) == 13 and isbn_13.isdigit()
        assert isbn_13.startswith('978')
        assert check_digit_13(isbn_13[:-1]) == isbn_13[-1]
    except AssertionError:
        return
    return isbn_13[3:-1] + check_digit_10(isbn_13[3:-1])

def isbn_10_to_isbn_13(isbn_10):
    isbn_10 = isbn_10.replace('-', '')
    try:
        assert len(isbn_10) == 10 and isbn_10[:-1].isdigit()
        assert check_digit_10(isbn_10[:-1]) == isbn_10[-1]
    except AssertionError:
        return
    isbn_13 = '978' + isbn_10[:-1]
    return isbn_13 + check_digit_13(isbn_13)

def opposite_isbn(isbn): # ISBN10 -> ISBN13 and ISBN13 -> ISBN10
    isbn = isbn.replace('-', '')
    for f in isbn_13_to_isbn_10, isbn_10_to_isbn_13:
        alt = f(isbn)
        if alt:
            return alt

def both_isbns(isbn):
    """Returns both isbn_10 and isbn_13 from given ISBN.
    The given ISBN can be either isbn-10 or isbn-13.
    """
    if isbn is None:
        return None, None
    else:
        return to10(isbn), to13(isbn)

def to13(isbn):
    """Converts the isbn to 13 digit isbn.
    The given ISBN can be either isbn-10 or isbn-13.
    """
    if not isbn:
        return None

    isbn = isbn.replace("-", "")
    if len(isbn) == 13:
        return isbn
    elif len(isbn) == 10:
        return isbn_10_to_isbn_13(isbn)
    else:
        return None

def to10(isbn):
    """Converts the isbn to 10 digit isbn.
    The given ISBN can be either isbn-10 or isbn-13.
    """
    if not isbn:
        return None

    isbn = isbn.replace("-", "")
    if len(isbn) == 10:
        return isbn
    elif len(isbn) == 13:
        return isbn_13_to_isbn_10(isbn)
    else:
        return None