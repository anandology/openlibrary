from datastore import Datastore

from .views.edition_identifiers import EditionIdentifiersView
from .views.works import WorksView
from .views.work_authors import WorkAuthorsView
import sqlalchemy as sa

class OLStore(Datastore):
    """Datastore for managing Open Library documents.    
    """
    tablename = "olstore"
    
    def create_views(self):
        return {
            'edition-identifiers': EditionIdentifiersView(),
            'works': WorksView(),
            'work-authors': WorkAuthorsView(),
        }

    def get_coverid(self, identifier):
        """Returns coverid from edition identifier.
        
        This makes a query on edition-identifiers view and takes the first 
        available cover ordered by last_modified time of the edition.
        """
        identifier = identifier.strip().lower()
        rows = self.query("edition-identifiers", identifier=identifier, order_by="last_modified")
        rows = [row for row in rows if row['coverid'] > 0]
        if rows:
            return rows[0]['coverid']
        else:
            return -1
            
    def get_work_info(self, work_key):
        """Returns work document with editions and redirects added to it.
        
        The response is a dictionary containing all the key-value pairs of the 
        work document and two addional keys "editions" and "redirects". The 
        value of "editions" will be the list of edition documents that belong 
        to this work and the value of "redirects" will be the list of works 
        maked as redirect of this work.
        
        If there is no work with the specified key, None is returned.
        """
        rows = self.query("works", work_key=work_key, include_docs=True)
        docs = dict((row['_key'], row['_doc']) for row in rows)
        if work_key in docs:
            work = docs[work_key]
            work['editions'] = [doc for doc in docs.values() 
                                    if doc['type']['key'] == '/type/edition']
            work['redirects'] = [doc for doc in docs.values() 
                                    if doc['type']['key'] == '/type/redirect']
            return work
    
    def get_top_works(self, author_key, limit=1):
        """Returns the keys of works of the given author in the descending order of edition count.
        """
        view1 = self.views["works"]
        view2 = self.views["work-authors"]
        
        count = sa.func.count(view1.c._key).label("edition_count")
        
        query = (sa.select(columns=[count, view1.c.work_key])
                    .where(view1.c.work_key==view2.c._key)
                    .where(view1.c.type == "/type/edition")
                    .where(view2.c.author_key==author_key)
                    .group_by(view1.c.work_key)
                    .order_by(sa.desc("edition_count"))
                    .limit(limit)
                )
        
        rows = query.execute().fetchall()
        colnames = ["edition_count", "work_key"]
        return [dict(zip(colnames, row)) for row in rows]