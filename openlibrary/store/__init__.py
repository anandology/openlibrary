from datastore import Datastore

from edition_preview import EditionPreviewView
from edition_identifiers import EditionIdentifiersView

class OLStore(Datastore):
    tablename = "docs"
    
    def create_views(self):
        return {
            'edition-preview': EditionPreviewView(),
            'edition-identifiers': EditionIdentifiersView(),
        }