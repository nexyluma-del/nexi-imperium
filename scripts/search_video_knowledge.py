#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

import requests

from qdrant_video_knowledge import COLLECTION, QDRANT_URL, embedding


def main() -> int:
    parser = argparse.ArgumentParser(description="Search the local Qdrant video_knowledge collection.")
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    vector = embedding(args.query)
    response = requests.post(
        f"{QDRANT_URL}/collections/{COLLECTION}/points/search",
        json={"vector": vector, "limit": args.limit, "with_payload": True},
        timeout=60,
    )
    if response.status_code == 404:
        response = requests.post(
            f"{QDRANT_URL}/collections/{COLLECTION}/points/query",
            json={"query": vector, "limit": args.limit, "with_payload": True},
            timeout=60,
        )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("result")
    if isinstance(result, list):
        payload["result"] = result[: args.limit]
    elif isinstance(result, dict) and isinstance(result.get("points"), list):
        result["points"] = result["points"][: args.limit]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
