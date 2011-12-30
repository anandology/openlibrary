from datastore import View
import sqlalchemy as sa
from . import common
import web

class WorkAuthorsView(View):
    """View to map works to authors. 
    
    This view is used to find work-count and top-works of an author. To find 
    top-works of an author, this view is joined with works view.
    
    Sample rows:
    
        _key            auhthor_key
        /works/OL1W     /authors/OL1A
        /works/OL2W     /authors/OL2A
        /works/OL2W     /authors/OL3A
    """
    def get_table(self, metadata):
        return sa.Table("olstore_work_authors", metadata,
            sa.Column("author_key", sa.Unicode, index=True),
        )
        
    def map(self, doc):
        type = common.get_type(doc)
        
        if type == common.TYPE_WORK:
            for a in self.get_author_keys(doc):
                yield {
                    'author_key': a
                }

    def get_author_keys(self, work):
        """Returns keys of all authors of this work.
        """
        authors = work.get('authors') or []
        return [a['author']['key'] 
                for a in authors
                if 'author' in a and 'key' in a['author']]
                
        