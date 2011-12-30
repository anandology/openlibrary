from datastore import Datastore

from .views.edition_identifiers import EditionIdentifiersView
from .views.works import WorksView
from .views.work_authors import WorkAuthorsView

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
        """
        identifier = identifier.strip().lower()
        rows = self.query("edition-identifiers", identifier=identifier, order_by="last_modified")
        rows = [row for row in rows if row['coverid'] > 0]
        if rows:
            return rows[0]['coverid']
        else:
            return -1
        