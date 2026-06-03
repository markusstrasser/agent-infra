"""`corpus annotate ...` subcommand wiring."""
from __future__ import annotations

import argparse

from .annotate import annotate


def add_cli(subparsers) -> None:
    p = subparsers.add_parser(
        "annotate",
        help="Append a single annotation to a source's annotations.jsonl",
    )
    p.add_argument("--source-id", required=True,
                   help="canonical corpus source_id (doi_…, pmid_…, sha_…)")
    p.add_argument("--repo", required=True,
                   choices=["genomics", "phenome", "intel", "agent-infra", "research-mcp"])
    p.add_argument("--actor-type", required=True,
                   choices=["model", "human", "service", "cli"])
    p.add_argument("--actor-id", required=True,
                   help="urn:agent:<type>:<name>[@<version>]")
    p.add_argument("--scope", required=True,
                   help="free-form scope tag (e.g. raw_fetch, parse, claim_extraction, verdict)")
    p.add_argument("--tool", default=None)
    p.add_argument("--prompt-template-hash", default=None)
    p.add_argument("--output-uri", default=None,
                   help="corpus:// or project-root:// or <repo>:// URI to a sidecar output")
    p.add_argument("--output-hash", default=None)
    p.add_argument("--output-size-bytes", type=int, default=None)
    p.add_argument("--source-content-hash", default=None)
    p.add_argument("--supersedes", dest="supersedes_annotation_id", default=None)
    p.add_argument("--status", default="active",
                   choices=["active", "superseded", "retracted"])
    p.set_defaults(func=_run)


def _run(args: argparse.Namespace) -> int:
    annotation_id = annotate(
        args.source_id,
        store=args.corpus_store,
        repo=args.repo,
        actor_type=args.actor_type,
        actor_id=args.actor_id,
        scope=args.scope,
        tool=args.tool,
        prompt_template_hash=args.prompt_template_hash,
        output_uri=args.output_uri,
        output_hash=args.output_hash,
        output_size_bytes=args.output_size_bytes,
        source_content_hash=args.source_content_hash,
        supersedes_annotation_id=args.supersedes_annotation_id,
        status=args.status,
    )
    print(annotation_id)
    return 0
