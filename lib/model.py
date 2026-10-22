from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class ConfiguredBaseModel(BaseModel):
    __pydantic_config__ = ConfigDict(extra="ignore")


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
    avatarRegistered: bool
    # Zenn renamed `pro` to `plan` (2026-10); keep both optional so either schema validates.
    pro: bool | None = None
    plan: str | None = None


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
    sourceRepoUpdatedAt: datetime | None
    # Zenn split `pinned` into `pinnedByUser` / `pinnedByPublication` (2026-10).
    pinned: bool | None = None
    pinnedByUser: bool | None = None
    pinnedByPublication: bool | None = None
    path: str
    user: User
    publication: Publication | None


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
    articles: list[Article]
    nextPage: int | None = None


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
    dynamicIds: list[int]
    gip: bool
    scriptLoader: list
