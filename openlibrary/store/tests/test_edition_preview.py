from ..edition_preview import EditionPreviewView

class TestEditionPreviewView:
    def test_get_work(self):
        doc = {
            "key": "/books/OL1M",
            "type": {"key": "/type/edition"}
        }
        assert EditionPreviewView().get_work(doc) is None
        
        doc['works'] = []
        assert EditionPreviewView().get_work(doc) is None

        doc['works'] = [{"key": "/works/OL12345W"}]
        assert EditionPreviewView().get_work(doc) == "/works/OL12345W"

    def test_get_preview_data(self):
        doc = {
            "key": "/books/OL1M",
            "type": {"key": "/type/edition"}
        }
        assert EditionPreviewView().get_preview_data(doc) == {
            'key': '/books/OL1M',
            'title': '',
            'subtitle': '',
            'physical_format': None,
            'publishers': [],
            'publish_date': '',
            'languages': [],
            'covers': [],
            'identifiers': {}
        }