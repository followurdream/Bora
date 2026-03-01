from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib import parse, request


@dataclass
class ApiBuilder:
    """A tiny fluent builder for HTTP requests."""

    base_url: str
    path_segments: list[str] = field(default_factory=list)
    query_params: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    method: str = "GET"
    body_data: Any = None

    def path(self, *segments: str) -> "ApiBuilder":
        self.path_segments.extend(segment.strip("/") for segment in segments if segment)
        return self

    def query(self, **params: Any) -> "ApiBuilder":
        for key, value in params.items():
            if value is not None:
                self.query_params[key] = str(value)
        return self

    def header(self, key: str, value: str) -> "ApiBuilder":
        self.headers[key] = value
        return self

    def get(self) -> "ApiBuilder":
        self.method = "GET"
        self.body_data = None
        return self

    def post(self, data: Any) -> "ApiBuilder":
        self.method = "POST"
        self.body_data = data
        self.headers.setdefault("Content-Type", "application/json")
        return self

    def put(self, data: Any) -> "ApiBuilder":
        self.method = "PUT"
        self.body_data = data
        self.headers.setdefault("Content-Type", "application/json")
        return self

    def delete(self) -> "ApiBuilder":
        self.method = "DELETE"
        self.body_data = None
        return self

    def build_url(self) -> str:
        url = self.base_url.rstrip("/")
        if self.path_segments:
            url += "/" + "/".join(self.path_segments)
        if self.query_params:
            url += "?" + parse.urlencode(self.query_params)
        return url

    def build(self) -> request.Request:
        payload: bytes | None = None
        if self.body_data is not None:
            payload = json.dumps(self.body_data).encode("utf-8")

        return request.Request(
            url=self.build_url(),
            data=payload,
            headers=self.headers,
            method=self.method,
        )

    def send(self, timeout: float = 10.0) -> dict[str, Any]:
        req = self.build()
        with request.urlopen(req, timeout=timeout) as response:  # nosec: B310 (demo utility)
            body = response.read().decode("utf-8")
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                data = json.loads(body)
            else:
                data = body

            return {
                "status": response.status,
                "headers": dict(response.headers.items()),
                "data": data,
            }


def new_builder(base_url: str) -> ApiBuilder:
    return ApiBuilder(base_url=base_url)
