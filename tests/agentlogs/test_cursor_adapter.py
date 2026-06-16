from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agentlogs.adapters import cursor as cursor_adapter


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "cursor_sample.jsonl"


def test_discover_cursor_sources(tmp_path: Path) -> None:
    root = tmp_path / "projects" / "Users-alien-Projects-agent-infra" / "agent-transcripts"
    session_id = "16cb9652-6381-46ca-9e87-cdbe6b17e679"
    path = root / session_id / f"{session_id}.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(FIXTURE.read_text())

    sources = cursor_adapter.discover_sources(root=tmp_path / "projects")
    assert len(sources) == 1
    assert sources[0].vendor == "cursor"
    assert sources[0].path == path


def test_parse_cursor_source_extracts_messages_and_tools(tmp_path: Path) -> None:
    root = tmp_path / "projects" / "Users-alien-Projects-agent-infra" / "agent-transcripts"
    session_id = "16cb9652-6381-46ca-9e87-cdbe6b17e679"
    path = root / session_id / f"{session_id}.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(FIXTURE.read_text())

    bundle = cursor_adapter.parse_source(
        cursor_adapter.DiscoveredSource(
            vendor="cursor",
            source_kind="transcript_jsonl",
            path=path,
        )
    )

    assert len(bundle.sessions) == 1
    assert bundle.sessions[0].vendor == "cursor"
    assert bundle.sessions[0].client == "cursor-agent"
    assert bundle.sessions[0].project_slug == "agent-infra"
    assert bundle.sessions[0].project_root.endswith("/Projects/agent-infra")

    kinds = {event.kind for event in bundle.events}
    assert "user_message" in kinds
    assert "assistant_message" in kinds
    assert "tool_call" in kinds
    assert any(tc.tool_name == "Read" for tc in bundle.tool_calls)


def test_index_cursor_vendor(tmp_path: Path) -> None:
    import agentlogs
    from agentlogs import index as ix

    root = tmp_path / "projects" / "Users-alien-Projects-agent-infra" / "agent-transcripts"
    session_id = "16cb9652-6381-46ca-9e87-cdbe6b17e679"
    path = root / session_id / f"{session_id}.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(FIXTURE.read_text())

    db = agentlogs.connect(tmp_path / "cursor.db")
    stats = ix.index_vendor(db, "cursor", limit_sources=1, source_paths=[path])
    assert stats.sources_imported == 1
    assert stats.events_written > 0
    row = db.execute(
        "SELECT vendor, project_slug FROM sessions WHERE vendor='cursor'"
    ).fetchone()
    assert row["vendor"] == "cursor"
    assert row["project_slug"] == "agent-infra"
    db.close()
