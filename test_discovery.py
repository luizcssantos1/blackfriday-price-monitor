import unittest
import sqlite3
from datetime import datetime, timezone
from discovery import candidates, reserve, query_for

class DiscoveryTest(unittest.TestCase):
    def test_filters(self):
        base={"title":"Geladeira LG Side by Side 220V","url":"https://example.com/p","content":"R$ 2.999,90"}
        self.assertEqual(len(list(candidates([base,base]))),1)
        for title in ["Geladeira LG Side by Side 127V","Geladeira Consul Side by Side 220V","Geladeira LG Duplex 220V","Geladeira LG Side by Side 220V usada"]:
            self.assertEqual(list(candidates([dict(base,title=title)])),[])
        self.assertEqual(list(candidates([dict(base,content="R$ 5.500,00")])),[])
    def test_description_and_installments(self):
        base={"title":"Geladeira LG Side by Side","url":"https://example.com/p","content":"220V R$ 2.999,90"}
        self.assertEqual(len(list(candidates([base]))),1)
        self.assertEqual(list(candidates([dict(base,content="220V 10x de R$ 599,90")])),[])
        self.assertEqual(list(candidates([dict(base,content="220V R$ 2.999,90 R$ 5.999,90")])),[])
    def test_rotation(self):
        from datetime import timedelta
        now=datetime(2026,11,27,12,tzinfo=timezone.utc)
        self.assertNotEqual(query_for(now),query_for(now+timedelta(hours=1)))
    def test_quota(self):
        with sqlite3.connect(":memory:") as db:
            now=datetime(2026,11,27,12,tzinfo=timezone.utc)
            self.assertTrue(reserve(db,now))
            self.assertFalse(reserve(db,now))
if __name__ == "__main__":
    unittest.main()
