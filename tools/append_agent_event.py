import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Append a validated agent event to agent_events.jsonl safely."
    )
    parser.add_argument("--session", type=int, required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--type", required=True)
    parser.add_argument("--stage", choices=["proposed", "implemented", "validated"], required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--points", type=int, required=True)
    parser.add_argument("--impact", choices=["low", "medium", "high", "critical"], required=True)
    parser.add_argument("--target-agent")
    parser.add_argument("--timestamp")
    parser.add_argument("--validated", choices=["true", "false"])
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    events_path = repo_root / "agent_events.jsonl"

    if args.timestamp:
        timestamp = args.timestamp
    else:
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    if args.validated is None:
        validated = args.stage == "validated"
    else:
        validated = args.validated == "true"

    event = {
        "timestamp": timestamp,
        "session": args.session,
        "agent": args.agent,
        "type": args.type,
        "stage": args.stage,
        "title": args.title,
        "description": args.description,
        "points": args.points,
        "impact": args.impact,
        "validated": validated,
    }
    if args.target_agent:
        event["target_agent"] = args.target_agent

    existing = []
    if events_path.exists():
        with events_path.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if line:
                    existing.append(json.loads(line))

    duplicate = any(
        row.get("session") == event["session"]
        and row.get("agent") == event["agent"]
        and row.get("title") == event["title"]
        for row in existing
    )
    if duplicate:
        raise SystemExit(
            f"Duplicate event blocked for session={event['session']} agent={event['agent']} title={event['title']!r}"
        )

    payload = json.dumps(event, ensure_ascii=False)
    if args.dry_run:
        print(payload)
        return

    with events_path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(payload + "\n")

    print(f"Appended event to {events_path}")


if __name__ == "__main__":
    main()
