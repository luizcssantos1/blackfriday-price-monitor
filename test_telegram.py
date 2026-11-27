import unittest
import sqlite3
from telegram_notify import notify, canonical

class TelegramTest(unittest.TestCase):
    def test_dedup(self):
        with sqlite3.connect(":memory:") as db:
            sent=[]
            self.assertTrue(notify(db,"offer:4999","test",sent.append))
            self.assertFalse(notify(db,"offer:4999","test",sent.append))
            self.assertTrue(notify(db,"offer:4599","test",sent.append))
            self.assertEqual(len(sent),2)
    def test_retry(self):
        with sqlite3.connect(":memory:") as db:
            def fail(message):
                raise RuntimeError("failed")
            with self.assertRaises(RuntimeError):
                notify(db,"test","test",fail)
            self.assertTrue(notify(db,"test","test",lambda message: None))
    def test_tracking(self):
        self.assertEqual(canonical("https://example.com/p?utm_source=x"),canonical("https://example.com/p"))

if __name__=="__main__":
    unittest.main()
