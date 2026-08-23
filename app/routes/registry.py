"""Route registry for the production FastAPI app.

The route handlers are still imported from the compatibility module while
business logic continues moving into services. This registry makes the runtime
application modular today: every legacy endpoint is grouped into a domain router
before it is mounted on the ASGI app.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute


ROUTE_ORDER = ("public", "agent", "payment", "admin", "static")


@dataclass(frozen=True, slots=True)
class RouteRegistry:
    """Summary of legacy routes mounted through modular routers."""

    public: tuple[str, ...]
    agent: tuple[str, ...]
    payment: tuple[str, ...]
    admin: tuple[str, ...]
    static: tuple[str, ...]

    @property
    def total(self) -> int:
        return sum(len(getattr(self, name)) for name in ROUTE_ORDER)

    def as_dict(self) -> dict[str, list[str] | int]:
        data = {name: list(getattr(self, name)) for name in ROUTE_ORDER}
        data["total"] = self.total
        return data


def legacy_api_routes(legacy_app: FastAPI) -> list[APIRoute]:
    """Return only user-defined API/page routes from a legacy FastAPI app."""

    return [route for route in legacy_app.routes if isinstance(route, APIRoute)]


def route_category(path: str) -> str:
    """Return the modular router category for a legacy path."""

    if path.startswith("/api/agent"):
        return "agent"
    if path.startswith("/api/admin") or path.startswith("/api/debug") or path == "/api/transactions":
        return "admin"
    if (
        path.startswith("/api/self-pay")
        or path in {
            "/api/pay",
            "/api/kassa/pay",
            "/api/add-drink",
            "/api/edit-request",
            "/api/round-request",
            "/api/deduct-round",
            "/api/deduct-round-preview",
            "/api/member-message/ack",
        }
    ):
        return "payment"
    if (
        path == "/"
        or path.startswith("/liste")
        or path in {"/admin", "/kassa", "/kassa/", "/self-pay", "/self-pay/", "/bezahlen", "/bezahlen/"}
        or path.endswith(".webmanifest")
        or path.endswith(".js")
        or path.endswith(".png")
        or path.endswith(".svg")
    ):
        return "static"
    return "public"


def build_route_registry(routes: Iterable[APIRoute]) -> tuple[dict[str, APIRouter], RouteRegistry]:
    """Group legacy routes into APIRouters and return a registry summary."""

    routers = {name: APIRouter(tags=[name]) for name in ROUTE_ORDER}
    paths: dict[str, list[str]] = {name: [] for name in ROUTE_ORDER}
    for route in routes:
        category = route_category(route.path)
        routers[category].routes.append(route)
        paths[category].append(route.path)
    registry = RouteRegistry(**{name: tuple(paths[name]) for name in ROUTE_ORDER})
    return routers, registry


def include_legacy_routes(app: FastAPI, legacy_app: FastAPI) -> RouteRegistry:
    """Mount all legacy APIRoutes on ``app`` through categorized routers."""

    routers, registry = build_route_registry(legacy_api_routes(legacy_app))
    for name in ROUTE_ORDER:
        app.include_router(routers[name])
    app.state.route_registry = registry.as_dict()
    return registry
