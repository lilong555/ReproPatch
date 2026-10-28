"""CPA 的固定入口与 SSH 回环路由。"""

from dataclasses import asdict, dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class CPARoute:
    name: str
    logical_endpoint: str
    base_url: str
    trust_env: bool

    def accepts(self, url):
        """每条路由只开放固定主机、端口和 Responses 路径。"""
        expected = urlsplit(self.base_url)
        if hasattr(url, "host"):
            scheme, host, port, path = url.scheme, url.host, url.port, url.path
            invalid = any((url.query, url.fragment, url.username, url.password))
        else:
            actual = urlsplit(str(url))
            scheme, host, port, path = actual.scheme, actual.hostname, actual.port, actual.path
            invalid = any((actual.query, actual.fragment, actual.username, actual.password))
        return (
            scheme == expected.scheme
            and host == expected.hostname
            and (port or 443) == (expected.port or 443)
            and path == expected.path + "/responses"
            and not invalid
        )

    def to_dict(self):
        return asdict(self)


ROUTES = {
    "public": CPARoute(
        "public", "https://cpa.liyinlong.me/v1", "https://cpa.liyinlong.me/v1", True
    ),
    "azure-ssh": CPARoute(
        "azure-ssh", "https://cpa.liyinlong.me/v1", "http://127.0.0.1:18317/v1", False
    ),
}


def cpa_route(name="public"):
    try:
        return ROUTES[name]
    except (KeyError, TypeError) as error:
        raise ValueError("CPA_ROUTE_REJECTED") from error
