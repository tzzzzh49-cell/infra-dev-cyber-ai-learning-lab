#!/usr/bin/env python3
"""Fail when a live FastAPI route is missing from the generated OpenAPI schema."""

from app.main import app

HTTP_METHODS = {"delete", "get", "head", "options", "patch", "post", "put", "trace"}
FASTAPI_INTERNAL_ROUTES = {
    "openapi",
    "redoc_html",
    "swagger_ui_html",
    "swagger_ui_redirect",
}


def main() -> int:
    active = {
        (route.path, method.lower())
        for route in app.routes
        if route.name not in FASTAPI_INTERNAL_ROUTES
        for method in (getattr(route, "methods", None) or ())
        if method.lower() in HTTP_METHODS
    }
    schema = app.openapi()
    documented = {
        (path, method)
        for path, operations in schema.get("paths", {}).items()
        for method in operations
        if method in HTTP_METHODS
    }

    for path, method in sorted(active):
        print(f"{method.upper():7} {path}")

    missing = active - documented
    if missing:
        print("Routes actives absentes du schéma OpenAPI:")
        for path, method in sorted(missing):
            print(f"- {method.upper()} {path}")
        return 1

    print("Toutes les routes actives sont documentées dans OpenAPI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
