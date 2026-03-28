from pydantic import BaseModel


class BookSearchResult(BaseModel):
    title: str
    authors: list[str]
    isbn13: str
    publisher: str
    price: int
    sale_price: int
    thumbnail: str
    pub_date: str


class BookSearchResponse(BaseModel):
    books: list[BookSearchResult]
    total_count: int
    is_end: bool
    page: int
