"""
Human-in-the-loop approval step.
"""

import time
from typing import Optional, Callable
from uniflow.core.step import Step
from uniflow.core.context import Context

class ApprovalStep(Step):
    """
    A step that pauses execution until manual approval is granted.
    
    This is useful for:
    - Reviewing LLM outputs before proceeding
    - Cost control (approving expensive operations)
    - Safety checks
    
    The step will poll for approval status or wait for a signal.
    """
    
    def __init__(
        self,
        name: str,
        approver: Optional[str] = None,
        timeout_seconds: int = 3600, # 1 hour default
        auto_approve_if: Optional[Callable] = None
    ):
        super().__init__(name)
        self.approver = approver
        self.timeout_seconds = timeout_seconds
        self.auto_approve_if = auto_approve_if
        
    def __call__(self, *args, **kwargs):
        """Execute the approval logic."""
        
        # Check auto-approval condition
        if self.auto_approve_if and self.auto_approve_if(*args, **kwargs):
            print(f"✅ Auto-approved step '{self.name}'")
            return args[0] if args else None
            
        print(f"✋ Step '{self.name}' requires approval.")
        print(f"   Waiting for approval from: {self.approver or 'Any'}")
        print(f"   Timeout: {self.timeout_seconds}s")
        
        # In a real implementation, this would:
        # 1. Create an 'Approval Request' in the DB
        # 2. Send a notification (Slack/Email)
        # 3. Poll DB for status change
        
        # For this local version, we'll simulate a simple CLI prompt if interactive,
        # or just fail if non-interactive (safety first).
        
        # Check if we are in an interactive terminal
        import sys
        if sys.stdin.isatty():
            response = input(f"   Approve execution? [y/N]: ")
            if response.lower() == 'y':
                print(f"✅ Approved.")
                return args[0] if args else None
            else:
                raise RuntimeError(f"Step '{self.name}' was rejected by user.")
        else:
            # Non-interactive mode - check for a file or env var?
            # For now, we'll just raise an error saying manual intervention needed
            # In a real system, this would block/suspend the workflow state.
            raise RuntimeError("Manual approval required but running in non-interactive mode. Implement persistent state storage to handle async approvals.")

def approval(name: str = "approval", **kwargs):
    """Decorator/helper to create an approval step."""
    return ApprovalStep(name, **kwargs)
