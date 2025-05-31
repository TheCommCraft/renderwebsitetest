from typing import Generic, TypeVar
from asyncio import Lock, Queue, run, create_task, sleep, Task, Semaphore

D = TypeVar("D")
class DataEvent(Generic[D]):
    _wait_lock: Lock
    _push_sem: Semaphore
    _push_lock: Lock
    _queue: Queue[D]
    _waiters: int
    def __init__(self):
        self._wait_lock = Lock()
        self._push_sem = Semaphore(0)
        self._push_lock = Lock()
        self._queue = Queue()
        self._waiters = 0
    
    async def await_data(self) -> D:
        try:
            async with self._wait_lock:
                self._waiters += 1
                self._push_sem.release()
                if not self._push_lock.locked():
                    await self._push_lock.acquire()
            data = await self._queue.get()
            self._waiters = 0
            return data
        finally:
            if not self._push_sem.locked():
                await self._push_sem.acquire()
            if not self._push_sem.locked() and self._push_lock.locked():
                self._push_lock.release()
    
    async def _push_data(self, data: D) -> None:
        await self._queue.put(data)
    
    async def push_data(self, data: D) -> None:
        async with self._wait_lock:
            for _ in range(self._waiters):
                await self._push_data(data)
            async with self._push_lock:
                pass
if __name__ == "__main__":
    event: DataEvent[str] = DataEvent()

    async def test_task(name: str):
        for _ in range(5):
            print(f"{name}: {await event.await_data()}")

    async def schedule_task(task: Task, tasks: set[Task]):
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    async def test():
        tasks = set()
        await schedule_task(create_task(test_task("A")), tasks)
        await schedule_task(create_task(test_task("B")), tasks)
        await sleep(0)
        for i in range(5):
            print(">>>", i)
            await event.push_data(str(i))

    run(test())