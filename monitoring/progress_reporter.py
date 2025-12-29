"""
Progress Reporter - Simple synchronous wrapper for monitoring API
Allows simulator and analysis to report progress without async complexity
"""

import time
import uuid
import requests
from typing import Optional, Dict
from contextlib import contextmanager


class ProgressReporter:
    """Synchronous progress reporter for monitoring API"""

    def __init__(self, base_url: str = "http://localhost:8765", enabled: bool = True):
        self.base_url = base_url
        self.enabled = enabled
        self.session = requests.Session()
        self.session.timeout = 2.0  # Fast timeout
        self.current_process_id: Optional[str] = None

        # Test connection
        if self.enabled:
            try:
                response = self.session.get(f"{self.base_url}/", timeout=1.0)
                if response.status_code != 200:
                    print(f"Warning: Monitoring API not responding, disabling progress reporting")
                    self.enabled = False
            except:
                print(f"Warning: Cannot connect to monitoring API at {self.base_url}, disabling progress reporting")
                self.enabled = False

    def register(self, process_type: str, total_items: int,
                process_id: Optional[str] = None, metadata: Dict = {}) -> str:
        """Register a new process and return process ID"""
        if not self.enabled:
            return f"disabled_{uuid.uuid4().hex[:8]}"

        if not process_id:
            process_id = f"{process_type}_{uuid.uuid4().hex[:8]}"

        try:
            response = self.session.post(
                f"{self.base_url}/process/register",
                json={
                    "process_id": process_id,
                    "process_type": process_type,
                    "status": "running",
                    "current": 0,
                    "total": total_items,
                    "message": "Started",
                    "timestamp": time.time(),
                    "metadata": metadata
                },
                timeout=2.0
            )

            if response.status_code == 200:
                self.current_process_id = process_id
                return process_id
            else:
                print(f"Warning: Failed to register process: {response.status_code}")
                return process_id

        except Exception as e:
            print(f"Warning: Could not register process: {e}")
            return process_id

    def update(self, current: int, message: str = "", process_id: Optional[str] = None):
        """Update progress"""
        if not self.enabled:
            return

        pid = process_id or self.current_process_id
        if not pid:
            return

        try:
            self.session.post(
                f"{self.base_url}/process/update",
                json={
                    "process_id": pid,
                    "process_type": "simulation",  # Ignored by API
                    "status": "running",
                    "current": current,
                    "total": 0,  # Will use existing total
                    "message": message,
                    "timestamp": time.time(),
                    "metadata": {}
                },
                timeout=1.0
            )
        except:
            pass  # Silently fail for updates

    def complete(self, message: str = "Completed successfully", process_id: Optional[str] = None):
        """Mark process as completed"""
        if not self.enabled:
            return

        pid = process_id or self.current_process_id
        if not pid:
            return

        try:
            self.session.post(
                f"{self.base_url}/process/{pid}/complete",
                params={"message": message},
                timeout=2.0
            )
            if pid == self.current_process_id:
                self.current_process_id = None
        except:
            pass

    def fail(self, error_message: str, process_id: Optional[str] = None):
        """Mark process as failed"""
        if not self.enabled:
            return

        pid = process_id or self.current_process_id
        if not pid:
            return

        try:
            self.session.post(
                f"{self.base_url}/process/{pid}/fail",
                params={"error_message": error_message},
                timeout=2.0
            )
            if pid == self.current_process_id:
                self.current_process_id = None
        except:
            pass

    @contextmanager
    def track_process(self, process_type: str, total_items: int, metadata: Dict = {}):
        """Context manager for automatic process tracking"""
        process_id = self.register(process_type, total_items, metadata=metadata)

        try:
            yield process_id
            self.complete(process_id=process_id)
        except Exception as e:
            self.fail(str(e), process_id=process_id)
            raise


# Singleton instance for easy access
_global_reporter: Optional[ProgressReporter] = None


def get_reporter(base_url: str = "http://localhost:8765") -> ProgressReporter:
    """Get or create global progress reporter"""
    global _global_reporter
    if _global_reporter is None:
        _global_reporter = ProgressReporter(base_url=base_url)
    return _global_reporter


def disable_reporting():
    """Disable progress reporting globally"""
    global _global_reporter
    if _global_reporter:
        _global_reporter.enabled = False
