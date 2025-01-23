from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, HttpUrl


class ConfiguredBaseModel(BaseModel):
    __pydantic_config__ = ConfigDict()
    # __pydantic_config__ = ConfigDict(extra="ignore")


class User(ConfiguredBaseModel):
    id: int
    username: str
    name: str
    avatarSmallUrl: HttpUrl


class Publication(ConfiguredBaseModel):
    id: int
    name: str
    displayName: str
    avatarSmallUrl: HttpUrl
    avatarUrl: HttpUrl
    pro: bool
    avatarRegistered: bool


class Article(ConfiguredBaseModel):
    id: int
    postType: str
    title: str
    slug: str
    commentsCount: int
    likedCount: int
    bookmarkedCount: int
    bodyLettersCount: int
    articleType: str
    emoji: str
    isSuspendingPrivate: bool
    publishedAt: datetime
    bodyUpdatedAt: datetime
    sourceRepoUpdatedAt: Optional[datetime]
    pinned: bool
    path: str
    user: User
    publication: Optional[Publication]


class ResTopic(ConfiguredBaseModel):
    id: int
    name: str
    taggingsCount: int
    imageUrl: HttpUrl
    displayName: str
    articlesCount: int
    booksCount: int
    scrapsCount: int


class PageProps(ConfiguredBaseModel):
    resTopic: ResTopic
    isContest: bool
    currentPage: int
    activeItemType: str
    articles: List[Article]
    nextPage: Optional[int] = None


class Props(ConfiguredBaseModel):
    pageProps: PageProps


class Query(ConfiguredBaseModel):
    name: str


class SEModel(ConfiguredBaseModel):
    props: Props
    page: str
    query: Query
    buildId: str
    assetPrefix: HttpUrl
    isFallback: bool
    isExperimentalCompile: bool
    dynamicIds: List[int]
    gip: bool
    scriptLoader: List
