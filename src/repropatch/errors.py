class ReproPatchError(Exception):
    """A user-facing, non-secret error."""


class PolicyError(ReproPatchError):
    """An attempted tool action violates the task policy."""


class InfrastructureError(ReproPatchError):
    """Execution infrastructure failed; this is not a test failure."""
