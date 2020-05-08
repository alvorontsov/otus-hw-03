import unittest

from redis.exceptions import ConnectionError
from mock import patch, MagicMock
import fakeredis

import store


class TestStore(unittest.TestCase):

    @patch("redis.StrictRedis", fakeredis.FakeStrictRedis)
    def test_cache_get(self):
        redis_storage = store.RedisStorage()
        redis_storage.db.connected = False
        storage = store.Storage(redis_storage)
        self.assertEqual(storage.cache_get("key"), None)

    @patch("redis.StrictRedis", fakeredis.FakeStrictRedis)
    def test_cache_set(self):
        redis_storage = store.RedisStorage()
        redis_storage.db.connected = False
        storage = store.Storage(redis_storage)
        self.assertEqual(storage.cache_set("key", "value"), True)

    @patch("redis.StrictRedis", fakeredis.FakeStrictRedis)
    def test_retry_get_on_connection_error(self):
        redis_storage = store.RedisStorage()
        redis_storage.db.connected = False
        redis_storage.db.get = MagicMock(side_effect=ConnectionError())
        storage = store.Storage(redis_storage)
        self.assertEqual(storage.cache_get("key"), None)
        self.assertEqual(redis_storage.db.get.call_count, store.Storage.MAX_RETRIES)

    @patch("redis.StrictRedis", fakeredis.FakeStrictRedis)
    def test_retry_set_on_connection_error(self):
        redis_storage = store.RedisStorage()
        redis_storage.db.connected = False
        redis_storage.db.set = MagicMock(side_effect=ConnectionError())
        storage = store.Storage(redis_storage)
        self.assertEqual(storage.cache_set("key", "value"), None)
        self.assertEqual(redis_storage.db.set.call_count, store.Storage.MAX_RETRIES)


if __name__ == "__main__":
    unittest.main()