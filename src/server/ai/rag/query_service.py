# -*- coding: utf-8 -*-
import re


class QueryProcessor:
    def normalize(self, query: str) -> str:
        query = query or ""
        query = query.replace("\u3000", " ")
        query = re.sub(r"\s+", " ", query)
        return query.strip()

    def expand(self, query: str, business_type: str | None = None) -> list[str]:
        return [self.normalize(query)]

    def validate(self, query: str) -> tuple[bool, str]:
        query = self.normalize(query)
        if not query:
            return False, "问题不能为空"
        if len(query) < 2:
            return False, "问题过短，请输入更完整的问题"
        return True, query


query_processor = QueryProcessor()
