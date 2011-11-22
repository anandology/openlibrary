from datastore import View
from . import common

class EditionIdentifiersView(View):
    """View to store edition identifiers.
    
    The table for this view stores one row for each identifier.
    
        /books/OL1M     isbn:123456789X
        /books/OL1M     isbn:9781234567897
        /books/OL1M     ia:foo12bar
        /books/OL1M     lccn:55012090
        /books/OL1M     librarything:1264202
        ...
    """
    def get_table(self, metadata):
        """Schema of the view table.
        """
        return sa.Table("edition_identifiers", metadata,
            sa.Column("identifier", sa.Unicode, index=True)
        )
    
    def map(self, doc):
        if common.get_type(doc) == common.TYPE_EDITION:
            ids = common.get_edition_identifiers(doc)
            isbns = ids.pop('isbn_10', []) + ids.pop('isbn_13', [])
            ids['isbn'] = self.massage_isbns(isbns)
        
            for name, values in ids.items():
                for v in values:
                    yield {
                        'identifier': name.lower() + ":" + v
                    }
        
    def massage_isbns(self, isbns):
        x = set()
        x.update(isbnlib.to10(isbn) for isbn in isbns)
        x.update(isbnlib.to13(isbn) for isbn in isbns)
        # to10/to13 returns None when there is a bad-isbn. Remove it from the set.
        x.discard(None)
        return list(x)