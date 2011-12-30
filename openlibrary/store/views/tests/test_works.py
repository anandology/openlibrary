from ..works import WorksView

class TestWorksView:
    def test_get_work_of_edition(self):
        f = WorksView().get_work_of_edition
        assert f({}) == None
        
        doc = {
            'works': []
        }
        assert f(doc) == None
        
        doc = {
            'works': [
                {'key': '/works/OL1W'}
            ]
        }
        assert f(doc) == '/works/OL1W'

    def map(self, doc):
        return list(WorksView().map(doc))
        
    def test_map_with_edition(self):
        doc = {
            'key': '/books/OL1M',
            'type': {'key': '/type/edition'},
            'works': [
                {'key': '/works/OL1W'}
            ]
        }
            
        assert self.map(doc) == [{
            'type': '/type/edition',
            'work_key': '/works/OL1W'
        }]
        
        doc = {
            'key': '/books/OL1M',
            'type': {'key': '/type/edition'},
        }
        assert self.map(doc) == [{
            'type': '/type/edition',
            'work_key': None
        }]
        
    def test_map_with_work(self):
        doc = {
            'key': '/works/OL1W',
            'type': {'key': '/type/work'},
        }
            
        assert self.map(doc) == [{
            'type': '/type/work',
            'work_key': '/works/OL1W'
        }]

    def test_map_with_redirect(self):
        doc = {
            'key': '/works/OL1W',
            'type': {'key': '/type/redirect'},
            'location': '/works/OL2W'
        }
        assert self.map(doc) == [{
            'type': '/type/redirect',
            'work_key': '/works/OL2W'
        }]
    
    def test_map_with_non_work_redirect(self):
        doc = {
            'key': '/books/OL1M',
            'type': {'key': '/type/redirect'},
            'location': '/books/OL2M'
        }
        assert self.map(doc) == []

    def test_map_with_other_types(self):
        # deleted documents shouldn't contribute to the view
        doc = {
            'key': '/books/OL1M',
            'type': {'key': '/type/delete'},
            'works': [
                {'key': '/works/OL1W'}
            ]
        }
        assert self.map(doc) == []

        # even other types shouldn't contribute anything
        doc = {
            'key': '/foo',
            'type': {'key': '/type/page'},
            'works': [
                {'key': '/works/OL1W'}
            ]
        }
        assert self.map(doc) == []
        