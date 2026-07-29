from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy import delete
from sqlalchemy.orm import Session

from .config import get_settings
from .db import SessionLocal
from .models import AuditEvent, IncidentReport


CONFIRMATION = "DELETE-DEMO-INCIDENTS"


@dataclass(frozen=True)
class PurgeResult:
    incidents: int
    audit_events: int


def purge_demo_incidents(
    db: Session,
    *,
    deployment_tier: str,
    confirmation: str,
) -> PurgeResult:
    if deployment_tier != "demo":
        raise RuntimeError("Incident cleanup is restricted to the demo deployment.")
    if confirmation != CONFIRMATION:
        raise RuntimeError(f"Confirmation must be exactly {CONFIRMATION}.")

    audit_result = db.execute(
        delete(AuditEvent).where(AuditEvent.entity_type == "incident")
    )
    incident_result = db.execute(delete(IncidentReport))
    db.commit()
    return PurgeResult(
        incidents=incident_result.rowcount or 0,
        audit_events=audit_result.rowcount or 0,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Restricted maintenance commands for PIMASCOR incident reports."
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    purge = subcommands.add_parser(
        "purge",
        help="Permanently delete demo incident reports and their incident audit events.",
    )
    purge.add_argument(
        "--confirm",
        required=True,
        help=f"Required safety phrase: {CONFIRMATION}",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()
    if args.command != "purge":
        raise SystemExit("Unsupported command.")

    try:
        with SessionLocal() as db:
            result = purge_demo_incidents(
                db,
                deployment_tier=settings.deployment_tier,
                confirmation=args.confirm,
            )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    print(
        "Demo incident cleanup completed: "
        f"{result.incidents} incident report(s) and "
        f"{result.audit_events} incident audit event(s) deleted."
    )
    print("Users, business records, documents, Podman secrets, and email are unchanged.")


if __name__ == "__main__":
    main()
