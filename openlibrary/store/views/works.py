from datastore import View
import sqlalchemy as sa
from . import common
import web

class WorksView(View):
    """View to creating mapping from work-key to editions, redirects and the work it self.
    
    This view is useful to get all the information about a work including its 
    editions and redirects. Useful for solr indexing.
    
    This view is also useful to compute edition-count of a work.
    
    Sample rows:
    
        _key            work_key        type
        /books/OL1M     /works/OL1W     /type/edition
        /books/OL2M     /works/OL1W     /type/edition
        /works/OL1W     /works/OL1W     /type/work
        /works/OL2W     /works/OL1W     /type/redirect
    """
    def get_table(self):
        table = sa.Table("olstore_works", metadata,
            sa.Column("work_key", sa.Unicode),
            sa.Column("type", sa.Unicode),
        )
        sa.Index('olstore_works_idx', table.c.work_key, table.c.type)
        return table
        
    def map(self, doc):
        type = common.get_type(doc)
        
        if type == common.TYPE_EDITION:
            work = self.get_work_of_edition(doc)
            yield {
                'type': type,
                'work_key': work
            }
        elif type == common.TYPE_WORK:
            yield {
                'type': type,
                'work_key': doc['key'] 
            }
        elif type == common.TYPE_REDIRECT and doc['key'].startswith("/works/"):
            yield {
                'type': type,
                'work_key': doc['location']
            }
            
    def get_work_of_edition(self, edition):
        """Returns work-key of the given edition.
        
        Returns None if the given edition doesn't belong to any work.
        """
        works = edition.get('works') or []
        if works and 'key' in works[0]:
            return works[0]['key']