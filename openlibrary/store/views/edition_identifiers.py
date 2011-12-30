from datastore import View
import sqlalchemy as sa
from . import common
import web

from openlibrary.core import helpers as h
from openlibrary.utils import isbn as isbnlib

class EditionIdentifiersView(View):
    """View to store edition identifiers.
    
    The table for this view stores one row for each identifier.
    
        /books/OL1M     isbn:123456789X         1234    2011-01-02T03:04:05
        /books/OL1M     isbn:9781234567897      1234    2011-01-02T03:04:05
        /books/OL1M     ia:foo12bar             1234    2011-01-02T03:04:05
        /books/OL1M     lccn:55012090           1234    2011-01-02T03:04:05
        /books/OL1M     librarything:1264202    1234    2011-01-02T03:04:05
        ...
    """
    
    def get_table(self, metadata):
        """Schema of the view table.
        """
        return sa.Table("olstore_edition_identifiers", metadata,
            sa.Column("identifier", sa.Unicode, index=True),
            sa.Column("coverid", sa.Integer),
            sa.Column("last_modified", sa.DateTime),
        )
    
    def map(self, doc):
        if common.get_type(doc) == common.TYPE_EDITION:
            ids = common.get_edition_identifiers(doc)
            
            # massage isbns
            isbns = ids.pop('isbn_10', []) + ids.pop('isbn_13', [])
            ids['isbn'] = self.massage_isbns(isbns)
            
            # get coverid and last_modified
            covers = doc.get('covers') or []
            coverid = web.listget(covers, 0, -1)
            last_modified = h.parse_datetime(doc['last_modified']['value'])
        
            # emit rows
            for name, values in ids.items():
                for v in values:
                    yield {
                        'identifier': name.lower() + ":" + v,
                        'coverid': coverid,
                        'last_modified': last_modified
                    }
        
    def massage_isbns(self, isbns):
        x = set()
        x.update(isbnlib.to10(isbn) for isbn in isbns)
        x.update(isbnlib.to13(isbn) for isbn in isbns)
        # to10/to13 returns None when there is a bad-isbn. Remove it from the set.
        x.discard(None)
        return list(x)
        
