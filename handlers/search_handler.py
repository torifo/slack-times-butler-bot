from __future__ import annotations

from services.search_service import SearchService


class SearchHandler:
    def __init__(self, search_service: SearchService):
        self.search_service = search_service

    def handle(self, query: str) -> str:
        results = self.search_service.search(query=query)
        return self.search_service.format_results(results)
