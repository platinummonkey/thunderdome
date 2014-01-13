# -*- coding: utf-8 -*-
from unittest import skip
from thunderdome import connection
from thunderdome.exceptions import ThunderdomeException
from thunderdome.tests.base import BaseThunderdomeTestCase

from thunderdome.tests.models import TestModel, TestEdge

from thunderdome import gremlin
from thunderdome import models
from thunderdome.models import Edge, Vertex
from thunderdome import properties


class OtherTestModel(Vertex):
    count = properties.Integer()
    text  = properties.Text()


class AliasedTestModel(Vertex):
    count = properties.Integer(db_field='how_many')
    text = properties.Text()


class OtherTestEdge(Edge):
    numbers = properties.Integer()


class YetAnotherTestEdge(Edge):
    numbers = properties.Integer()


class TestVertexIO(BaseThunderdomeTestCase):

    def test_unicode_io(self):
        """
        Tests that unicode is saved and retrieved properly
        """
        tm1 = TestModel.create(count=9, text=u'4567ë9989')
        tm2 = TestModel.get(tm1.vid)

    def test_model_save_and_load(self):
        """
        Tests that models can be saved and retrieved
        """
        tm0 = TestModel.create(count=8, text='123456789')
        tm1 = TestModel.create(count=9, text='456789')
        tms = TestModel.all([tm0.vid, tm1.vid])

        assert len(tms) == 2
       
        for cname in tm0._columns.keys():
            self.assertEquals(getattr(tm0, cname), getattr(tms[0], cname))
            
        tms = TestModel.all([tm1.vid, tm0.vid])
        assert tms[0].vid == tm1.vid 
        assert tms[1].vid == tm0.vid 
            
    def test_model_updating_works_properly(self):
        """
        Tests that subsequent saves after initial model creation work
        """
        tm = TestModel.create(count=8, text='123456789')

        tm.count = 100
        tm.save()

        tm.count = 80
        tm.save()

        tm.count = 60
        tm.save()

        tm.count = 40
        tm.save()

        tm.count = 20
        tm.save()

        tm2 = TestModel.get(tm.vid)
        self.assertEquals(tm.count, tm2.count)

    def test_model_deleting_works_properly(self):
        """
        Tests that an instance's delete method deletes the instance
        """
        tm = TestModel.create(count=8, text='123456789')
        vid = tm.vid
        tm.delete()
        with self.assertRaises(TestModel.DoesNotExist):
            tm2 = TestModel.get(vid)

    def test_reload(self):
        """ Tests that and instance's reload method does an inplace update of the instance """
        tm0 = TestModel.create(count=8, text='123456789')
        tm1 = TestModel.get(tm0.vid)
        tm1.count = 7
        tm1.save()

        tm0.reload()
        self.assertEqual(tm0.count, 7)

    def test_reload_on_aliased_field(self):
        """ Tests that reload works with aliased fields """
        tm0 = AliasedTestModel.create(count=8, text='123456789')
        tm1 = AliasedTestModel.get(tm0.vid)
        tm1.count = 7
        tm1.save()

        tm0.reload()
        self.assertEqual(tm0.count, 7)


class DeserializationTestModel(Vertex):
    count = properties.Integer()
    text = properties.Text()

    gremlin_path = 'deserialize.groovy'

    get_map = gremlin.GremlinValue()
    get_list = gremlin.GremlinMethod()


class TestNestedDeserialization(BaseThunderdomeTestCase):
    """
    Tests that vertices are properly deserialized when nested in map and list data structures
    """

    def test_map_deserialization(self):
        """
        Tests that elements nested in maps are properly deserialized
        """
        
        original = DeserializationTestModel.create(count=5, text='happy')
        nested = original.get_map()

        self.assertIsInstance(nested, dict)
        self.assertEqual(nested['vertex'], original)
        self.assertEqual(nested['number'], 5)

    def test_list_deserialization(self):
        """
        Tests that elements nested in lists are properly deserialized
        """
        
        original = DeserializationTestModel.create(count=5, text='happy')
        nested = original.get_list()

        self.assertIsInstance(nested, list)
        self.assertEqual(nested[0], None)
        self.assertEqual(nested[1], 0)
        self.assertEqual(nested[2], 1)

        self.assertIsInstance(nested[3], list)
        self.assertEqual(nested[3][0], 2)
        self.assertEqual(nested[3][1], original)
        self.assertEqual(nested[3][2], 3)

        self.assertEqual(nested[4], 5)


class TestUpdateMethod(BaseThunderdomeTestCase):
    def test_success_case(self):
        """ Tests that the update method works as expected """
        tm = TestModel.create(count=8, text='123456789')
        tm2 = tm.update(count=9)

        tm3 = TestModel.get(tm.vid)
        self.assertEqual(tm2.count, 9)
        self.assertEqual(tm3.count, 9)

    def test_unknown_names_raise_exception(self):
        """ Tests that passing in names for columns that don't exist raises an exception """
        tm = TestModel.create(count=8, text='123456789')
        with self.assertRaises(TypeError):
            tm.update(jon='beard')


class TestVertexTraversal(BaseThunderdomeTestCase):

    def setUp(self):
        super(TestVertexTraversal, self).setUp()
        self.v1 = TestModel.create(count=1, text='Test1')
        self.v2 = TestModel.create(count=2, text='Test2')
        self.v3 = OtherTestModel.create(count=3, text='Test3')
        self.v4 = OtherTestModel.create(count=3, text='Test3')

    def test_outgoing_vertex_traversal(self):
        """Test that outgoing vertex traversals work."""
        e1 = TestEdge.create(self.v1, self.v2, numbers=12)
        e2 = TestEdge.create(self.v1, self.v3, numbers=13)
        e3 = TestEdge.create(self.v2, self.v3, numbers=14)

        results = self.v1.outV(TestEdge)
        self.assertEqual(len(results), 2)
        self.assertIn(self.v2, results)
        self.assertIn(self.v3, results)

        results = self.v1.outV(TestEdge, types=[OtherTestModel])
        self.assertEqual(len(results), 1)
        self.assertIn(self.v3, results)

    def test_incoming_vertex_traversal(self):
        """Test that incoming vertex traversals work."""
        e1 = TestEdge.create(self.v1, self.v2, numbers=12)
        e2 = TestEdge.create(self.v1, self.v3, numbers=13)
        e3 = TestEdge.create(self.v2, self.v3, numbers=14)

        results = self.v2.inV(TestEdge)
        self.assertEqual(len(results), 1)
        self.assertIn(self.v1, results)

        results = self.v2.inV(TestEdge, types=[OtherTestModel])
        self.assertEqual(len(results), 0)

    def test_outgoing_edge_traversals(self):
        """Test that outgoing edge traversals work."""
        e1 = TestEdge.create(self.v1, self.v2, numbers=12)
        e2 = TestEdge.create(self.v1, self.v3, numbers=13)
        e3 = OtherTestEdge.create(self.v2, self.v3, numbers=14)

        results = self.v2.outE()
        self.assertEqual(len(results), 1)
        self.assertIn(e3, results)

        results = self.v2.outE(types=[TestEdge])
        self.assertEqual(len(results), 0)

    def test_incoming_edge_traversals(self):
        """Test that incoming edge traversals work."""
        e1 = TestEdge.create(self.v1, self.v2, numbers=12)
        e2 = TestEdge.create(self.v1, self.v3, numbers=13)
        e3 = OtherTestEdge.create(self.v2, self.v3, numbers=14)

        results = self.v2.inE()
        self.assertEqual(len(results), 1)
        self.assertIn(e1, results)

        results = self.v2.inE(types=[OtherTestEdge])
        self.assertEqual(len(results), 0)

    def test_multiple_label_traversals(self):
        """ Tests that using multiple edges for traversals works """
        TestEdge.create(self.v1, self.v2)
        OtherTestEdge.create(self.v1, self.v3)
        YetAnotherTestEdge.create(self.v1, self.v4)

        self.assertEqual(len(self.v1.outV()), 3)

        self.assertEqual(len(self.v1.outV(TestEdge)), 1)
        self.assertEqual(len(self.v1.outV(OtherTestEdge)), 1)
        self.assertEqual(len(self.v1.outV(YetAnotherTestEdge)), 1)

        out = self.v1.outV(TestEdge, OtherTestEdge)
        self.assertEqual(len(out), 2)
        self.assertIn(self.v2.vid, [v.vid for v in out])
        self.assertIn(self.v3.vid, [v.vid for v in out])

        out = self.v1.outV(OtherTestEdge, YetAnotherTestEdge)
        self.assertEqual(len(out), 2)
        self.assertIn(self.v3.vid, [v.vid for v in out])
        self.assertIn(self.v4.vid, [v.vid for v in out])

    def test_multiple_edge_traversal_with_type_filtering(self):
        """ Tests that using multiple edges for traversals works """
        v = TestModel.create(count=1, text='Test1')

        v1 = TestModel.create()
        TestEdge.create(v, v1)

        v2 = TestModel.create()
        OtherTestEdge.create(v, v2)

        v3 = TestModel.create()
        YetAnotherTestEdge.create(v, v3)

        v4 = OtherTestModel.create()
        TestEdge.create(v, v4)

        v5 = OtherTestModel.create()
        OtherTestEdge.create(v, v5)

        v6 = OtherTestModel.create()
        YetAnotherTestEdge.create(v, v6)

        self.assertEqual(len(v.outV()), 6)

        self.assertEqual(len(v.outV(TestEdge, OtherTestEdge)), 4)
        self.assertEqual(len(v.outV(TestEdge, OtherTestEdge, types=[TestModel])), 2)

    def test_edge_instance_traversal_types(self):
        """ Test traversals with edge instances work properly """
        te = TestEdge.create(self.v1, self.v2)
        ote = OtherTestEdge.create(self.v1, self.v3)
        yate = YetAnotherTestEdge.create(self.v1, self.v4)

        out = self.v1.outV(te, ote)
        self.assertEqual(len(out), 2)
        self.assertIn(self.v2.vid, [v.vid for v in out])
        self.assertIn(self.v3.vid, [v.vid for v in out])

        out = self.v1.outV(ote, yate)
        self.assertEqual(len(out), 2)
        self.assertIn(self.v3.vid, [v.vid for v in out])
        self.assertIn(self.v4.vid, [v.vid for v in out])

    def test_edge_label_string_traversal_types(self):
        """ Test traversals with edge instances work properly """
        TestEdge.create(self.v1, self.v2)
        OtherTestEdge.create(self.v1, self.v3)
        YetAnotherTestEdge.create(self.v1, self.v4)

        out = self.v1.outV(TestEdge.get_label(), OtherTestEdge.get_label())
        self.assertEqual(len(out), 2)
        self.assertIn(self.v2.vid, [v.vid for v in out])
        self.assertIn(self.v3.vid, [v.vid for v in out])

        out = self.v1.outV(OtherTestEdge.get_label(), YetAnotherTestEdge.get_label())
        self.assertEqual(len(out), 2)
        self.assertIn(self.v3.vid, [v.vid for v in out])
        self.assertIn(self.v4.vid, [v.vid for v in out])

    def test_unknown_edge_traversal_filter_type_fails(self):
        """
        Tests an exception is raised if a traversal filter is
        used that's not an edge class, instance or label string fails
        """
        TestEdge.create(self.v1, self.v2)
        OtherTestEdge.create(self.v1, self.v3)
        YetAnotherTestEdge.create(self.v1, self.v4)

        with self.assertRaises(ThunderdomeException):
            out = self.v1.outV(5)

        with self.assertRaises(ThunderdomeException):
            out = self.v1.outV(True)


class TestIndexCreation(BaseThunderdomeTestCase):
    """
    Tests that automatic index creation works as expected
    """
    def setUp(self):
        super(TestIndexCreation, self).setUp()
        self.old_create_index = connection.create_key_index
        self.index_calls = []

        def new_create_index(name):
            #fire blanks
            self.index_calls.append(name)
            #return self.old_create_index(name)
        connection.create_key_index = new_create_index

        self.old_vertex_types = models.vertex_types
        models.vertex_types = {}

        self.old_index_setting = connection._index_all_fields

    def tearDown(self):
        super(TestIndexCreation, self).tearDown()
        models.vertex_types = self.old_vertex_types
        connection._index_all_fields = self.old_index_setting
        connection.create_key_index = self.old_create_index 

    def test_create_index_is_called(self):
        """
        Tests that create_key_index is called when defining indexed columns
        """
        self.assertEqual(len(self.index_calls), 0)

        connection._index_all_fields = False
        
        class TestIndexCreationCallTestVertex(Vertex):
            col1 = properties.Text(index=True)
            col2 = properties.Text(index=True, db_field='____column')
            col3 = properties.Text(db_field='____column3')

        self.assertEqual(len(self.index_calls), 2)
        self.assertNotIn('vid', self.index_calls)
        self.assertIn('col1', self.index_calls)
        self.assertIn('____column', self.index_calls)
        self.assertNotIn('____column3', self.index_calls)

        connection._index_all_fields = True
        self.index_calls = []

        class TestIndexCreationCallTestVertex2(Vertex):
            col1 = properties.Text()
            col2 = properties.Text(db_field='____column')

        self.assertEqual(len(self.index_calls), 3)
        self.assertIn('vid', self.index_calls)
        self.assertIn('col1', self.index_calls)
        self.assertIn('____column', self.index_calls)
