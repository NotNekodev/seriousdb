import json
import tempfile
import os
from fastapi import FastAPI
from fastapi import HTTPException
from threading import Lock


class Cache:
    def __init__(self):
        self.filename = None
        self.db = None
        self.lock = Lock()


def insert(key: str, value: str, cache: Cache):
    with cache.lock:
        if cache.db is None:
            raise HTTPException(
                status_code=404,
                detail=f"Database file {cache.filename} could not be opened and loaded",
            )
        cache.db[key] = value
    return value


def select(key: str, cache: Cache):
    with cache.lock:
        if cache.db is None:
            raise HTTPException(
                status_code=404,
                detail=f"Database file {cache.filename} could not be opened and loaded",
            )
        val = cache.db.get(key, None)
    if val is None:
        raise HTTPException(status_code=404, detail=f"No value set for key {key}")
    return val


def load(filename: str, cache: Cache):
    with cache.lock:
        db_file = filename
        if not os.path.isfile(db_file):
            with open(db_file, "wb") as f:
                json_dumps = json.dumps({"default": "default"}).encode()
                f.write(json_dumps)
            cache.db = {"default": "default"}
        else:
            with open(filename, "rb") as f:
                binary_text = f.read()
                json_text = binary_text.decode()
                cache.db = json.loads(json_text)
        cache.filename = filename


def file_write_atomic(path, data):
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")

    with os.fdopen(fd, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())  # synchronize the temporary file

    os.replace(tmp, path)  # atomically replace the temporary file with the actual one

    dir_fd = os.open(directory, os.O_DIRECTORY)
    os.fsync(dir_fd)  # synchronize the directory
    os.close(dir_fd)


def flush(cache: Cache):
    with cache.lock:
        if cache.db is None:
            return
        json_dumps = json.dumps(cache.db).encode()
        file_write_atomic(cache.filename, json_dumps)


db_file = ".sdb"
cache = Cache()
load(db_file, cache)

app = FastAPI()


@app.put("/db")
async def put(key: str, value: str):
    insert(key, value, cache)
    flush(cache)
    return value


@app.get("/db")
async def get(key: str):
    val = select(key, cache)
    return val
