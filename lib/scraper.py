import gzip
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from pydantic import HttpUrl
from tenacity import retry, stop_after_attempt, wait_exponential

from lib.tqdm import TqdmWrapper

type Robots = dict[str, list[tuple[str, str]]]


class WhiteScraper:
    robots_cache: dict[str, tuple[Robots, Optional[str]]] = {}

    def __init__(self, user_agent: str):
        self.user_agent = (
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) {user_agent}"
        )

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    async def open(self):
        self.client = httpx.AsyncClient(
            http2=True,
            headers={
                "user-agent": self.user_agent,
                "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Linux"',
                "upgrade-insecure-requests": "1",
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "sec-fetch-site": "none",
                "sec-fetch-mode": "navigate",
                "sec-fetch-user": "?1",
                "sec-fetch-dest": "document",
                "accept-encoding": "gzip",
                "accept-language": "ja,en;q=0.9",
            },
            timeout=httpx.Timeout(10.0, read=30.0),
        )

    async def close(self):
        await self.client.aclose()

    async def reopen(self):
        await self.close()
        await self.open()

    def robots_whitelist(self, host: str):
        self.robots_cache[host] = ({}, None)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=10, exp_base=2),
        after=lambda x: TqdmWrapper.print((str(x))),
        reraise=True,
    )
    async def request(self, method: str, url: HttpUrl, **kwargs):
        await self.robots_check(url)
        try:
            return await self.request_raw(method, url, **kwargs)
        except httpx.RemoteProtocolError:
            TqdmWrapper.print("Reopening connection")
            await self.reopen()
            return await self.request_raw(method, url, **kwargs)

    async def request_raw(self, method: str, url: HttpUrl, **kwargs):
        response = await self.client.request(method, str(url), **kwargs)
        response.raise_for_status()
        return response

    async def robots_check(self, url: HttpUrl):
        assert url.path is not None
        rules, _ = await self.__robots(url)
        if not self.__robots_txt_allowed(rules, url.path):
            raise ValueError("URL disallowed by robots.txt")

    async def sitemap(self, url: HttpUrl):
        assert url.host is not None
        _, sitemap = await self.__robots(url)
        if sitemap is None:
            raise ValueError("Sitemap not found")
        return HttpUrl(sitemap)

    async def get_sitemap(self, sitemap: HttpUrl):
        assert sitemap.scheme is not None
        assert sitemap.path is not None

        sitemap_xml = await self.request("GET", sitemap)
        if sitemap.path.endswith(".gz"):
            return self.__parse_sitemap(gzip.decompress(sitemap_xml.content).decode("utf-8"))
        return self.__parse_sitemap(sitemap_xml.text)

    async def __robots(self, url: HttpUrl):
        assert url.host is not None

        if url.host not in self.robots_cache.keys():
            robots = f"{url.scheme}://{url.host}/robots.txt"
            response = await self.request_raw("GET", HttpUrl(robots))
            self.robots_cache[url.host] = self.__parse_robots_txt(response.text)

        return self.robots_cache[url.host]

    def __parse_robots_txt(self, robots_txt: str) -> tuple[Robots, Optional[str]]:
        rules: Robots = {}

        current_user_agent = None
        sitemaps = None

        for line in robots_txt.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("user-agent:"):
                current_user_agent = line.split(":", 1)[1].strip()
                rules[current_user_agent] = []
            elif current_user_agent and (line.lower().startswith("allow:") or line.lower().startswith("disallow:")):
                directive, path = line.split(":", 1)
                rules[current_user_agent].append((directive.strip(), path.strip()))
            elif current_user_agent and line.lower().startswith("sitemap:"):
                sitemaps = line.split(":", 1)[1].strip()
        return rules, sitemaps

    def __robots_txt_allowed(self, rules: Robots, path: str) -> bool:
        allowed = True
        for match, rule in rules.items():
            if match == "*" or match in self.client.headers["user-agent"]:
                for directive, rule_path in rule:
                    if directive == "Allow" and path.startswith(rule_path):
                        allowed = True
                    elif directive == "Disallow" and path.startswith(rule_path):
                        allowed = False
        return allowed

    def __parse_sitemap(self, sitemap_xml: str) -> list[HttpUrl]:
        soup = BeautifulSoup(sitemap_xml, "xml")
        urls1 = [loc.find("loc").text for loc in soup.find_all("sitemap")]
        urls2 = [loc.find("loc").text for loc in soup.find_all("url")]
        return [HttpUrl(url) for url in urls1 + urls2]
