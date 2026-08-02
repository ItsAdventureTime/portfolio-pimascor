from datetime import date

from ..schemas import ReleaseChangeResponse, ReleaseUpdateResponse


# Change this release ID and date whenever a user-facing production update is
# published. Each user's last_seen_release_id makes the announcement appear
# once after that release, across devices and browsers.
CURRENT_RELEASE = ReleaseUpdateResponse(
    id="2026-08-03-workspace-refresh",
    released_on=date(2026, 8, 3),
    title="A smoother way to stay on top of every shipment",
    summary=(
        "PIMASCOR is easier to keep close, easier to recover, and clearer to use "
        "when work moves from one team to the next."
    ),
    changes=[
        ReleaseChangeResponse(
            kind="new",
            title="Install PIMASCOR as an app",
            description=(
                "Add PIMASCOR to your phone or computer Home Screen for one-tap "
                "access and a focused workspace."
            ),
        ),
        ReleaseChangeResponse(
            kind="new",
            title="Reset your password yourself",
            description=(
                "Use Forgot password? to receive a secure email link and get back "
                "to work without waiting for an administrator."
            ),
        ),
        ReleaseChangeResponse(
            kind="improved",
            title="Move through work with more confidence",
            description=(
                "Important workflow decisions, document access, and security "
                "messages are presented more clearly so the next step is easier to find."
            ),
        ),
    ],
)


def current_release_update() -> ReleaseUpdateResponse:
    return CURRENT_RELEASE.model_copy(deep=True)
