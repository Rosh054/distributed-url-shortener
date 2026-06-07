#!/usr/bin/env python3
"""Generate short URLs for load testing."""

import argparse
import json
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk-create short URLs")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--output", default="results/generated_urls.json")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    created: list[dict[str, str]] = []
    with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
        health = client.get("/health")
        health.raise_for_status()

        for index in range(args.count):
            response = client.post(
                "/shorten",
                json={"long_url": f"https://example.com/page/{index}"},
            )
            response.raise_for_status()
            body = response.json()
            created.append(
                {
                    "short_code": body["short_code"],
                    "short_url": body["short_url"],
                    "long_url": body["long_url"],
                }
            )

    output_path.write_text(json.dumps({"count": len(created), "urls": created}, indent=2))
    print(f"Created {len(created)} URLs -> {output_path}")


if __name__ == "__main__":
    main()
