import asyncio
import glob
import json
import os
from typing import Optional, TypeVar

import aiofiles
import httpx
from bs4 import BeautifulSoup
from PIL import Image
from pydantic import HttpUrl

from lib.model import SEModel
from lib.scraper import WhiteScraper
from lib.tqdm import TqdmWrapper

T = TypeVar("T")
CDN = "storage.googleapis.com"
TqdmWrapper.ci = os.environ.get("CI", "false").lower() == "true"


def google_storage_filter(url: str) -> bool:
    return url.startswith("https://storage.googleapis.com/zenn-user-upload/topics/") and url.endswith(".png")


def find_one(data: list[T]) -> T:
    if len(data) == 1:
        return data[0]
    else:
        raise ValueError("Multiple elements found")


def find_one_or_none(data: list[T]) -> Optional[T]:
    if len(data) == 1:
        return data[0]
    elif len(data) == 0:
        return None
    else:
        raise ValueError("Multiple elements found")


async def main():
    async with WhiteScraper("ZennCrawler/1.0.0+https://github.com/fa0311/zenn-icons") as client:
        client.robots_whitelist(CDN)
        sitemap = await client.sitemap(HttpUrl("https://zenn.dev"))
        urls = await client.get_sitemap(sitemap)
        topics = [url for url in urls if "topic" in (url.path or "")]
        topic_pages: list[HttpUrl] = []
        metadata = {}
        os.makedirs("images", exist_ok=True)

        for topic in topics:
            topic_pages.extend(await client.get_sitemap(topic))

        async def request(url: HttpUrl, name: str):
            try:
                return await client.request("GET", url)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    TqdmWrapper.print(f"Not found: {name} {url}")
                    return None

        async def process_pages(page: HttpUrl, semaphore=asyncio.Semaphore(2)):
            assert page.path is not None
            async with semaphore:
                html = await client.request("GET", page)
            soup = BeautifulSoup(html.text, "html.parser")
            next_data = soup.find_all("script", {"type": "application/json", "id": "__NEXT_DATA__"})

            data = SEModel.model_validate_json(find_one(find_one(next_data).contents))
            topic = data.props.pageProps.resTopic
            metadata[topic.name] = topic.model_dump(mode="json")
            if topic.imageUrl.host == CDN:
                res = await request(topic.imageUrl, topic.name)
                if res is not None:
                    async with aiofiles.open(f"images/{topic.name}.png", "wb") as f:
                        await f.write(res.content)
                    TqdmWrapper.print(f"Downloaded {page}.png")

        await TqdmWrapper.gather(*[process_pages(page) for page in topic_pages])

        async with aiofiles.open("metadata.json", "w", encoding="utf-8") as f:
            await f.write(json.dumps(metadata, ensure_ascii=False, indent=2))

    for file in TqdmWrapper.tqdm([*glob.glob("images/*"), *glob.glob("zenn/*")]):
        name, ext = os.path.splitext(file)
        os.makedirs(f"dist/{os.path.dirname(name)}", exist_ok=True)
        if ext == ".png":
            with Image.open(file) as img:
                img.save(f"dist/{name}.webp", "WEBP", quality=80)
        else:
            async with aiofiles.open(file, "r") as f:
                async with aiofiles.open(f"dist/{name}{ext}", "w") as g:
                    await g.write(await f.read())


if __name__ == "__main__":
    asyncio.run(main())
