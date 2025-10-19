#!/usr/bin/env python3
"""Automated health check for the Codex vector stack."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from .client import CodexVectorClient


@dataclass
class QueryTest:
    name: str
    query: str
    limit: int = 5


@dataclass
class QueryResult:
    name: str
    passed: bool
    hits: int
    top_metadata: Optional[dict]
    notes: Optional[str] = None


@dataclass
class ResourceCheck:
    name: str
    where: dict


@dataclass
class ResourceResult:
    name: str
    passed: bool
    matches: int


@dataclass
class HealthReport:
    timestamp: str
    collection: str
    document_count: int
    query_tests: List[QueryResult] = field(default_factory=list)
    resource_checks: List[ResourceResult] = field(default_factory=list)


DEFAULT_QUERIES = [
    QueryTest(name="General search", query="codex vector database"),
    QueryTest(name="Runbook restart", query="kubectl rollout restart"),
    QueryTest(name="GitHub Actions guidance", query="autofix failing ci via codex"),
]

DEFAULT_RESOURCES = [
    ResourceCheck(
        name="OpenAI Cookbook – Autofix GitHub Actions",
        where={"doc_id": {"$eq": "openai-cookbook-codex-autofix-actions"}},
    ),
    ResourceCheck(
        name="Project README",
        where={"source": {"$eq": "README.md"}},
    ),
    ResourceCheck(
        name="Local runbook entry",
        where={"source": {"$eq": "runbook"}},
    ),
]


def run_query_tests(
    cli: CodexVectorClient, collection: str, tests: List[QueryTest]
) -> List[QueryResult]:
    results: List[QueryResult] = []
    for test in tests:
        try:
            matches = cli.query_results(collection, test.query, limit=test.limit)
        except Exception as exc:
            results.append(
                QueryResult(
                    name=test.name,
                    passed=False,
                    hits=0,
                    top_metadata=None,
                    notes=f"Query failed: {exc}",
                )
            )
            continue

        passed = bool(matches)
        top_meta = matches[0]["metadata"] if matches else None
        notes = None if passed else "No results returned"
        results.append(
            QueryResult(
                name=test.name,
                passed=passed,
                hits=len(matches),
                top_metadata=top_meta,
                notes=notes,
            )
        )
    return results


def run_resource_checks(
    cli: CodexVectorClient, collection: str, checks: List[ResourceCheck]
) -> List[ResourceResult]:
    collection_id = cli.get_collection_id(collection)
    results: List[ResourceResult] = []
    for check in checks:
        payload = {
            "where": check.where,
            "include": ["metadatas"],
            "limit": 1,
        }
        try:
            response = cli._request(
                "POST",
                cli._tenant_path(f"/collections/{collection_id}/get"),
                payload=payload,
            )
            metadatas = (response.payload or {}).get("metadatas") or []
            matches = len(metadatas)
            results.append(
                ResourceResult(name=check.name, passed=matches > 0, matches=matches)
            )
        except Exception:
            results.append(ResourceResult(name=check.name, passed=False, matches=0))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Codex stack health checks")
    parser.add_argument(
        "--collection", default="codex_agent", help="Collection name to validate"
    )
    parser.add_argument("--output", help="Optional path to write JSON report")
    args = parser.parse_args()

    cli = CodexVectorClient()
    collection_id = cli.get_collection_id(args.collection)
    document_count = cli._collection_count(collection_id)

    queries = run_query_tests(cli, args.collection, DEFAULT_QUERIES)
    resources = run_resource_checks(cli, args.collection, DEFAULT_RESOURCES)

    report = HealthReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        collection=args.collection,
        document_count=document_count,
        query_tests=queries,
        resource_checks=resources,
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(asdict(report), handle, indent=2)
        print(f"Health report written to {args.output}")
    else:
        print(json.dumps(asdict(report), indent=2))

    failures = [t for t in queries if not t.passed] + [
        r for r in resources if not r.passed
    ]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
