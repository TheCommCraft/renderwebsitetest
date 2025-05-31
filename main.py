from typing import Optional, Generic, TypeVar, TypedDict
from asyncio import Lock, Queue, timeout
from pathlib import Path
from json import dumps
from collections.abc import AsyncIterator
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, FileResponse

app = FastAPI()

D = TypeVar("D")
class DataEvent(Generic[D]):
    _wait_lock: Lock
    _queue: Queue[D]
    _last_waiter: int
    def __init__(self):
        self._wait_lock = Lock()
        self._queue = Queue()
        self._last_waiter = 0
    
    async def await_data(self) -> D:
        async with self._wait_lock:
            self._last_waiter += 1
            current_waiter = self._last_waiter
        data = await self._queue.get()
        async with self._wait_lock:
            if self._last_waiter != current_waiter:
                await self.push_data(data)
            else:
                self._last_waiter = 0
        return data
    
    async def push_data(self, data: D) -> None:
        await self._queue.put(data)

class Message(TypedDict):
    user: str
    message: str

message_event: DataEvent[Message] = DataEvent()
root_template = Path(__file__).parent / "index.html"

@app.get("/")
def root():
    return FileResponse(root_template)

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Optional[str] = None):
    return {"item_id": item_id, "q": q}

async def waiter() -> AsyncIterator[str]:
    try:
        async with timeout(60):
            while True:
                yield dumps(await message_event.await_data())+"\n"
    except TimeoutError:
        pass

@app.get("/streamtest/")
async def wait_stream():
    return StreamingResponse(waiter(), media_type="application/x-ndjson")

@app.post("/streamtest/")
async def send_data(user: str, message: str):
    await message_event.push_data({"user": user, "message": message})