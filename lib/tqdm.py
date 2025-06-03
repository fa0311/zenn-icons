import asyncio
import time
from typing import Awaitable, Iterable, TypeVar

import tqdm
from tqdm.asyncio import tqdm_asyncio

T = TypeVar("T")


class TqdmEventBase:
    def __init__(self, total: int):
        self.total = total
        self.current = 0
        self.start_time = time.time()

    def add(self):
        self.current += 1

    def print(self):
        elapsed = time.time() - self.start_time
        print(tqdm.tqdm.format_meter(self.current, self.total, elapsed, 80))

    def close(self):
        self.print()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class TqdmEvent(TqdmEventBase):
    def __init__(self, total: int):
        super().__init__(total)
        self.last_update = time.time()

    def add(self):
        super().add()
        if time.time() - self.last_update > 1:
            self.print()
            self.last_update = time.time()


class TqdmEventAsync(TqdmEventBase):
    def close(self):
        self.enabled = False
        return super().close()

    async def loop(self):
        self.enabled = True
        while self.enabled:
            self.print()
            await asyncio.sleep(1)

    def __enter__(self):
        asyncio.create_task(self.loop())
        return super().__enter__()


class TqdmWrapper:
    ci = False

    @staticmethod
    def print(message: str):
        if TqdmWrapper.ci:
            print(message)
        else:
            tqdm_asyncio.write(message)

    @staticmethod
    async def run_sync(fs: Awaitable[T], pbar: TqdmEventAsync):
        res = await fs
        pbar.add()
        return res

    @staticmethod
    async def gather(*fs: Awaitable[T]):
        if TqdmWrapper.ci:
            with TqdmEventAsync(len(fs)) as pbar:
                return await asyncio.gather(*[TqdmWrapper.run_sync(f, pbar) for f in fs])
        else:
            return await tqdm_asyncio.gather(*fs)

    @staticmethod
    def tqdm(iterable: Iterable[T]) -> Iterable[T]:
        if TqdmWrapper.ci:
            with TqdmEvent(len(list(iterable))) as pbar:
                for item in iterable:
                    yield item
                    pbar.add()
        else:
            yield from tqdm.tqdm(iterable)
