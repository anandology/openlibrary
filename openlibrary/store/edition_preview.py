"""Edition preview view.
"""

from datastore import View, DataType
import web

from openlibrary.utils import isbn as isbnlib
from . import common

class EditionPreviewView(View):
    """View to store edition preview data.
    
    This view contains three columns:
        * _key - key of the edition
        * work - key of the work
        * preview - preview data stores as gzipped JSON
    
    The edition preview data is used to display editions on the works page.
    
    The preview data contains the following fields:
    
        * key - key of the edition
        * title - title of the edition
        * subtitle - subtitle or empty
        * identifiers - dict of identifiers with each value as a list. 
                        Includes isbn_10, isbn_13, lccn, oclc_numbers and ia.
        * covers - list of cover ids
        * physical_format - Physical format
        * publish_date - Published date as string
        * publishers - List of publishers
        * borrow_status - one of "available" | "checkedout" if the book is borrowable, None otherwise.
        * ia_collections - List of ia collections if the book has an iaid (ocaid).
        
    The preview data always contains all these fields except the last two.
    When a field not available in the doc, it will be empty string or None.
    """
    def get_table(self, metadata):
        """Schema of the index view."""
        return sa.Table("edition_preview", metadata,
            sa.Column("work", sa.Unicode, index=True),
            sa.Column("preview", DataType(compress=True))
        )

    def map(self, doc):
        if common.get_type(doc) == common.TYPE_EDITION:
            yield {
                'work': self.get_work(doc),
                'preview': self.get_preview_data(doc)
            }
            
    def get_preview_data(self, doc):
        d = {
            'key': doc['key'],
            'title': doc.get('title', ''),
            'subtitle': doc.get('subtitle', ''),
            'physical_format': doc.get('physical_format'),
            'publish_date': doc.get('publish_date', ''),
            'publishers': doc.get('publishers', []),
            'covers': doc.get('covers', []),
            'languages': doc.get('languages', []),
            'identifiers': common.get_edition_identifiers(doc)
        }
        
        if '_borrow_status' in doc:
            d['borrow_status'] = doc['_borrow_status']
        
        if '_ia_collections' in doc:
            d['ia_collections'] = doc['_ia_collections']
        
        return d
            
    def get_work(self, doc):
        try:
            return doc.get('works', [])[0]['key']
        except IndexError:
            return None

class EditionPreview(web.storage):
    """Model class for edition preview data.
    """
    @property
    def isbn_10(self):
        isbns = self.identifiers.get("isbn_10", []) + self.identifiers.get("isbn_13", [])
        if isbns:
            return isbnlib.to10(isbns[0])

    @property
    def isbn_13(self):
        isbns = self.identifiers.get("isbn_13", []) + self.identifiers.get("isbn_10", [])
        if isbns:
            return isbnlib.to13(isbns[0])