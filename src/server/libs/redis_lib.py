# -*- coding: utf-8 -*-
import json
import redis
from fastapi import Request
from src.configs import get_setting

settings = get_setting()
redis_store = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


# rq_job_queue = rq.Queue(connection=redis_store, name='job_queue')
# rq_train_queue = rq.Queue(connection=redis_store, name='llm_training')

def redis_sismember(key, value):
    if redis_store.sismember(key, value):
        return True
    else:
        return False


def redis_sadd(key, value):
    if redis_store.sismember(key, value):
        return False
    else:
        redis_store.sadd(key, value)
        return True


def redis_set(key, value, ex=86400):
    value = json.dumps(value)
    redis_result = redis_store.set(key, value, ex=ex)
    return redis_result


def redis_hset(key, field, value):
    """
    key: conversation id
    field: file id
    value : file content
    """
    if isinstance(value, str):
        redis_store.hset(key, field, value)
    else:
        redis_store.hset(key, field, json.dumps(value))
    redis_store.expire(key, 300)


def redis_hget(key, field):
    store: bytes
    if store := redis_store.hget(key, field):
        return store.decode('utf-8')


def redis_hget_all(key):
    bytes_decode_dict = dict()
    if store := redis_store.hgetall(key):
        for k in store:
            bytes_decode_dict[k.decode('utf-8')] = store.get(k).decode('utf-8')
        return bytes_decode_dict


def redis_list_set(key, value, ex=86400):
    list_length = redis_store.lpush(key, value)
    redis_store.expire(key, ex)
    return list_length


def redis_list_get(key, start_index=0, end_index=-1):
    if result := redis_store.lrange(key, start_index, end_index):
        return result
    else:
        return None


def redis_get(key):
    redis_result = redis_store.get(key)
    if redis_result:
        return json.loads(redis_result)
    return []


def redis_remove(key):
    result = redis_store.delete(key)
    return result


def register_rate_limit(request: Request, email):
    client_ip = request.client.host
    block_key = f"register:block:{client_ip}:{email}"
    request_count = redis_store.incr(block_key)
    redis_store.expire(block_key, settings.REDIS_BLOCK_TIME)
    if request_count > settings.REDIS_REQUEST_REQUEST_LIMIT:
        return True
    else:
        return False


if __name__ == '__main__':
    count = redis_store.incr('test1')
    print(count)
