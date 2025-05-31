from typing import Optional
from asyncio import timeout
from pathlib import Path
from collections.abc import AsyncIterator
from data_event import DataEvent
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

app = FastAPI()

class Message(BaseModel):
    user: str
    message: str
    user_id: int

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
                yield (await message_event.await_data()).model_dump_json()+"\n"
    except TimeoutError:
        pass

@app.get("/streamtest/")
async def wait_stream():
    return StreamingResponse(waiter(), media_type="application/x-ndjson")

@app.post("/streamtest/")
async def send_data(message: Message):
    await message_event.push_data(message)