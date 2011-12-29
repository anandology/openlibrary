from datastore import Datastore

from edition_preview import EditionPreviewView
from edition_identifiers import EditionIdentifiersView

class OLStore(Datastore):
    tablename = "olstore"
    
    def create_views(self):
        return {
            'edition-identifiers': EditionIdentifiersView(),
        }
        
        
store = OLStore