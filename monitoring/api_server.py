#!/usr/bin/env python3
"""
FastAPI Monitoring Server for BearishVanish
Provides real-time progress tracking and status monitoring without log files
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn


# ============================================================================
# Data Models
# ============================================================================

class ProcessStatus(str, Enum):
    """Process status enumeration"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class ProcessType(str, Enum):
    """Type of process being monitored"""
    DATA_DOWNLOAD = "data_download"
    SIMULATION = "simulation"
    ANALYSIS = "analysis"
    REPORT_GENERATION = "report_generation"
    VISUALIZATION = "visualization"


class ProgressUpdate(BaseModel):
    """Progress update from a running process"""
    process_id: str
    process_type: ProcessType
    status: ProcessStatus
    current: int
    total: int
    message: str
    timestamp: float
    metadata: Dict = {}


class ProcessInfo(BaseModel):
    """Complete information about a process"""
    process_id: str
    process_type: ProcessType
    status: ProcessStatus
    start_time: float
    end_time: Optional[float] = None
    current_progress: int = 0
    total_items: int = 0
    message: str = ""
    error_message: Optional[str] = None
    metadata: Dict = {}

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage"""
        if self.total_items == 0:
            return 0.0
        return (self.current_progress / self.total_items) * 100.0

    @property
    def elapsed_time(self) -> float:
        """Calculate elapsed time in seconds"""
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time

    @property
    def eta_seconds(self) -> Optional[float]:
        """Estimate time remaining in seconds"""
        if self.current_progress == 0 or self.total_items == 0:
            return None
        elapsed = self.elapsed_time
        rate = self.current_progress / elapsed
        remaining = self.total_items - self.current_progress
        return remaining / rate if rate > 0 else None


# ============================================================================
# Process Monitor (Shared State)
# ============================================================================

class ProcessMonitor:
    """Centralized process monitoring and state management"""

    def __init__(self, state_file: Path = Path("/tmp/bearishvanish_state.json")):
        self.state_file = state_file
        self.processes: Dict[str, ProcessInfo] = {}
        self.websocket_clients: List[WebSocket] = []
        self._load_state()

    def _load_state(self):
        """Load state from disk if exists"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    for proc_id, proc_data in data.items():
                        self.processes[proc_id] = ProcessInfo(**proc_data)
            except Exception as e:
                print(f"Warning: Could not load state: {e}")

    def _save_state(self):
        """Save current state to disk"""
        try:
            data = {k: v.dict() for k, v in self.processes.items()}
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save state: {e}")

    def register_process(self, process_id: str, process_type: ProcessType,
                        total_items: int = 0, metadata: Dict = {}) -> ProcessInfo:
        """Register a new process"""
        proc = ProcessInfo(
            process_id=process_id,
            process_type=process_type,
            status=ProcessStatus.RUNNING,
            start_time=time.time(),
            total_items=total_items,
            message="Process started",
            metadata=metadata
        )
        self.processes[process_id] = proc
        self._save_state()
        self._broadcast_update(proc)
        return proc

    def update_progress(self, process_id: str, current: int,
                       message: str = "", metadata: Dict = {}):
        """Update process progress"""
        if process_id not in self.processes:
            raise ValueError(f"Process {process_id} not registered")

        proc = self.processes[process_id]
        proc.current_progress = current
        if message:
            proc.message = message
        if metadata:
            proc.metadata.update(metadata)

        self._save_state()
        self._broadcast_update(proc)

    def complete_process(self, process_id: str, message: str = "Completed successfully"):
        """Mark process as completed"""
        if process_id not in self.processes:
            raise ValueError(f"Process {process_id} not registered")

        proc = self.processes[process_id]
        proc.status = ProcessStatus.COMPLETED
        proc.end_time = time.time()
        proc.message = message
        proc.current_progress = proc.total_items

        self._save_state()
        self._broadcast_update(proc)

    def fail_process(self, process_id: str, error_message: str):
        """Mark process as failed"""
        if process_id not in self.processes:
            raise ValueError(f"Process {process_id} not registered")

        proc = self.processes[process_id]
        proc.status = ProcessStatus.FAILED
        proc.end_time = time.time()
        proc.error_message = error_message
        proc.message = f"Failed: {error_message}"

        self._save_state()
        self._broadcast_update(proc)

    def get_process(self, process_id: str) -> Optional[ProcessInfo]:
        """Get process by ID"""
        return self.processes.get(process_id)

    def get_all_processes(self) -> List[ProcessInfo]:
        """Get all processes"""
        return list(self.processes.values())

    def get_running_processes(self) -> List[ProcessInfo]:
        """Get all running processes"""
        return [p for p in self.processes.values() if p.status == ProcessStatus.RUNNING]

    def get_processes_by_type(self, process_type: ProcessType) -> List[ProcessInfo]:
        """Get processes by type"""
        return [p for p in self.processes.values() if p.process_type == process_type]

    def clear_completed(self):
        """Clear completed and failed processes"""
        self.processes = {
            k: v for k, v in self.processes.items()
            if v.status in [ProcessStatus.RUNNING, ProcessStatus.PAUSED]
        }
        self._save_state()

    async def _broadcast_update(self, process: ProcessInfo):
        """Broadcast update to all websocket clients"""
        message = json.dumps(process.dict())
        dead_clients = []

        for client in self.websocket_clients:
            try:
                await client.send_text(message)
            except:
                dead_clients.append(client)

        # Remove disconnected clients
        for client in dead_clients:
            self.websocket_clients.remove(client)

    def add_websocket_client(self, websocket: WebSocket):
        """Add websocket client for real-time updates"""
        self.websocket_clients.append(websocket)

    def remove_websocket_client(self, websocket: WebSocket):
        """Remove websocket client"""
        if websocket in self.websocket_clients:
            self.websocket_clients.remove(websocket)


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="BearishVanish Monitoring API",
    description="Real-time monitoring of simulations, analysis, and data processing",
    version="1.0.0"
)

# Global process monitor
monitor = ProcessMonitor()


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """API root - health check"""
    return {
        "service": "BearishVanish Monitoring API",
        "status": "running",
        "version": "1.0.0",
        "timestamp": time.time()
    }


@app.get("/status")
async def get_status():
    """Get overall system status"""
    all_procs = monitor.get_all_processes()
    running = monitor.get_running_processes()

    return {
        "total_processes": len(all_procs),
        "running_processes": len(running),
        "completed_processes": len([p for p in all_procs if p.status == ProcessStatus.COMPLETED]),
        "failed_processes": len([p for p in all_procs if p.status == ProcessStatus.FAILED]),
        "timestamp": time.time()
    }


@app.get("/processes")
async def get_processes(status: Optional[str] = None, type: Optional[str] = None):
    """Get all processes, optionally filtered by status or type"""
    processes = monitor.get_all_processes()

    if status:
        try:
            status_enum = ProcessStatus(status)
            processes = [p for p in processes if p.status == status_enum]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if type:
        try:
            type_enum = ProcessType(type)
            processes = [p for p in processes if p.process_type == type_enum]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid type: {type}")

    return {
        "processes": [p.dict() for p in processes],
        "count": len(processes),
        "timestamp": time.time()
    }


@app.get("/process/{process_id}")
async def get_process(process_id: str):
    """Get specific process by ID"""
    proc = monitor.get_process(process_id)
    if not proc:
        raise HTTPException(status_code=404, detail=f"Process not found: {process_id}")

    return proc.dict()


@app.post("/process/register")
async def register_process(update: ProgressUpdate):
    """Register a new process"""
    proc = monitor.register_process(
        process_id=update.process_id,
        process_type=update.process_type,
        total_items=update.total,
        metadata=update.metadata
    )
    return proc.dict()


@app.post("/process/update")
async def update_process(update: ProgressUpdate):
    """Update process progress"""
    try:
        monitor.update_progress(
            process_id=update.process_id,
            current=update.current,
            message=update.message,
            metadata=update.metadata
        )
        return {"status": "updated", "process_id": update.process_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/process/{process_id}/complete")
async def complete_process(process_id: str, message: str = "Completed"):
    """Mark process as completed"""
    try:
        monitor.complete_process(process_id, message)
        return {"status": "completed", "process_id": process_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/process/{process_id}/fail")
async def fail_process(process_id: str, error_message: str):
    """Mark process as failed"""
    try:
        monitor.fail_process(process_id, error_message)
        return {"status": "failed", "process_id": process_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/processes/completed")
async def clear_completed():
    """Clear all completed and failed processes"""
    monitor.clear_completed()
    return {"status": "cleared", "timestamp": time.time()}


@app.get("/simulation/current")
async def get_current_simulation():
    """Get currently running simulation"""
    sims = monitor.get_processes_by_type(ProcessType.SIMULATION)
    running = [s for s in sims if s.status == ProcessStatus.RUNNING]

    if not running:
        return {"status": "no simulation running"}

    return running[0].dict()


@app.get("/analysis/current")
async def get_current_analysis():
    """Get currently running analysis"""
    analyses = monitor.get_processes_by_type(ProcessType.ANALYSIS)
    running = [a for a in analyses if a.status == ProcessStatus.RUNNING]

    if not running:
        return {"status": "no analysis running"}

    return running[0].dict()


@app.websocket("/ws/updates")
async def websocket_updates(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    monitor.add_websocket_client(websocket)

    try:
        # Send current state on connect
        all_procs = monitor.get_all_processes()
        await websocket.send_json({
            "type": "initial_state",
            "processes": [p.dict() for p in all_procs]
        })

        # Keep connection alive and handle messages
        while True:
            data = await websocket.receive_text()
            # Echo back for ping/pong
            await websocket.send_json({"type": "pong", "timestamp": time.time()})

    except WebSocketDisconnect:
        monitor.remove_websocket_client(websocket)


# ============================================================================
# Helper Client Functions (for integration into simulator/analysis)
# ============================================================================

class MonitoringClient:
    """Client for reporting progress to monitoring API"""

    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url
        self.session = None

    async def register(self, process_id: str, process_type: str, total: int, metadata: dict = {}):
        """Register new process"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/process/register",
                json={
                    "process_id": process_id,
                    "process_type": process_type,
                    "status": "running",
                    "current": 0,
                    "total": total,
                    "message": "Started",
                    "timestamp": time.time(),
                    "metadata": metadata
                }
            )
            return response.json()

    async def update(self, process_id: str, current: int, message: str = "", metadata: dict = {}):
        """Update progress"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/process/update",
                json={
                    "process_id": process_id,
                    "process_type": "simulation",  # Will be ignored
                    "status": "running",
                    "current": current,
                    "total": 0,
                    "message": message,
                    "timestamp": time.time(),
                    "metadata": metadata
                }
            )
            return response.json()

    async def complete(self, process_id: str, message: str = "Completed"):
        """Mark as completed"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/process/{process_id}/complete",
                params={"message": message}
            )
            return response.json()

    async def fail(self, process_id: str, error: str):
        """Mark as failed"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/process/{process_id}/fail",
                params={"error_message": error}
            )
            return response.json()


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Start the monitoring API server"""
    print("=" * 70)
    print("BearishVanish Monitoring API Server")
    print("=" * 70)
    print()
    print("Starting server on http://0.0.0.0:8765")
    print()
    print("Endpoints:")
    print("  GET  /                      - Health check")
    print("  GET  /status                - System status")
    print("  GET  /processes             - All processes")
    print("  GET  /process/{id}          - Specific process")
    print("  GET  /simulation/current    - Current simulation")
    print("  GET  /analysis/current      - Current analysis")
    print("  WS   /ws/updates            - Real-time updates")
    print()
    print("=" * 70)

    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")


if __name__ == "__main__":
    main()
