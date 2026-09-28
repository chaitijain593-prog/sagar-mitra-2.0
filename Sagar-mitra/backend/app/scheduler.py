"""
Sagar Mitra / ORCA - Oceanographic Task Scheduler Engine
=========================================================
Supports /schedule command execution:
1. Contextual Natural Language parsing of schedule queries (one-shot or recurring).
2. Background task executor polling SQLite `scheduled_tasks`.
3. Auto-appends completed execution results to the SQLite session transcript.
4. Emits real-time task events for in-app toast notification and chime audio.
"""
import asyncio
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any

from app.db_store import store as session_store

UNIT_MULTIPLIERS = {
    "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
    "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
    "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
    "d": 86400, "day": 86400, "days": 86400,
}


def parse_schedule_query(raw_query: str) -> Dict[str, Any]:
    """
    Parses natural language timing from user query.
    Extracts one-time or recurring schedule details and cleans the prompt.
    """
    text = raw_query.strip()
    if text.lower().startswith("/schedule"):
        text = text[9:].strip()

    now = datetime.now(timezone.utc)
    schedule_type = "once"
    interval_seconds = 0
    run_at_dt = None
    clean_prompt = text
    display_desc = ""

    # 1. Check for recurring: "every X (seconds|minutes|hours|days)"
    recurring_match = re.search(
        r'\bevery\s+(\d+)\s*(s(?:ec(?:ond)?s?)?|m(?:in(?:ute)?s?)?|h(?:(?:ou)?rs?)?|d(?:ays?)?)\b',
        text,
        re.IGNORECASE
    )
    if recurring_match:
        qty = int(recurring_match.group(1))
        unit = recurring_match.group(2).lower()
        multiplier = 60  # default
        for k, v in UNIT_MULTIPLIERS.items():
            if unit.startswith(k) or unit == k:
                multiplier = v
                break
        interval_seconds = max(5, qty * multiplier)
        schedule_type = "recurring"
        run_at_dt = now + timedelta(seconds=interval_seconds)
        display_desc = f"Recurring every {qty} {unit}"
        clean_prompt = re.sub(re.escape(recurring_match.group(0)), "", text, flags=re.IGNORECASE).strip()

    # 2. Check for one-shot delay: "in X (seconds|minutes|hours|days)" or "after X ..."
    if not run_at_dt:
        delay_match = re.search(
            r'\b(?:in|after)\s+(\d+)\s*(s(?:ec(?:ond)?s?)?|m(?:in(?:ute)?s?)?|h(?:(?:ou)?rs?)?|d(?:ays?)?)\b',
            text,
            re.IGNORECASE
        )
        if delay_match:
            qty = int(delay_match.group(1))
            unit = delay_match.group(2).lower()
            multiplier = 60
            for k, v in UNIT_MULTIPLIERS.items():
                if unit.startswith(k) or unit == k:
                    multiplier = v
                    break
            seconds = max(5, qty * multiplier)
            schedule_type = "once"
            run_at_dt = now + timedelta(seconds=seconds)
            display_desc = f"One-time in {qty} {unit}"
            clean_prompt = re.sub(re.escape(delay_match.group(0)), "", text, flags=re.IGNORECASE).strip()

    # 3. Check for specific time: "at HH:MM (am/pm)?"
    if not run_at_dt:
        at_match = re.search(r'\bat\s+(\d{1,2}):(\d{2})(?:\s*(am|pm))?\b', text, re.IGNORECASE)
        if at_match:
            hr = int(at_match.group(1))
            minute = int(at_match.group(2))
            meridiem = (at_match.group(3) or "").lower()
            if meridiem == "pm" and hr < 12:
                hr += 12
            elif meridiem == "am" and hr == 12:
                hr = 0
            
            target_dt = now.replace(hour=hr, minute=minute, second=0, microsecond=0)
            if target_dt <= now:
                target_dt += timedelta(days=1)
            schedule_type = "once"
            run_at_dt = target_dt
            display_desc = f"One-time at {hr:02d}:{minute:02d} UTC"
            clean_prompt = re.sub(re.escape(at_match.group(0)), "", text, flags=re.IGNORECASE).strip()

    # 4. Contextual fallback if timing was underspecified
    if not run_at_dt:
        if re.search(r'\b(periodically|recurring|continuously|daily)\b', text, re.IGNORECASE):
            schedule_type = "recurring"
            interval_seconds = 3600  # 1 hour
            run_at_dt = now + timedelta(seconds=interval_seconds)
            display_desc = "Recurring every 1 hour (Default)"
        else:
            schedule_type = "once"
            interval_seconds = 15
            run_at_dt = now + timedelta(seconds=15)
            display_desc = "One-time in 15 seconds (Prompt Run)"

    clean_prompt = re.sub(r'^(?:please\s+|can\s+you\s+|to\s+)', '', clean_prompt, flags=re.IGNORECASE).strip()
    if not clean_prompt:
        clean_prompt = "Oceanographic telemetry status check"

    return {
        "schedule_type": schedule_type,
        "run_at": run_at_dt.isoformat(),
        "interval_seconds": interval_seconds,
        "clean_prompt": clean_prompt,
        "display_desc": display_desc
    }


def _execute_orchestration_sync(task: Dict[str, Any]) -> Dict[str, Any]:
    """Helper invoked in a background thread to call run_orchestration safely."""
    from app.main import run_orchestration, OrchestrateRequest
    import json

    coords = [18.922, 72.833]
    try:
        raw_coords = task.get("coordinates")
        if isinstance(raw_coords, str):
            coords = json.loads(raw_coords)
        elif isinstance(raw_coords, list):
            coords = raw_coords
    except Exception:
        pass

    session_id = task.get("session_id") or f"session_sched_{int(datetime.now().timestamp())}"
    prompt = task.get("prompt", "Analyze ocean telemetry")
    workspace_id = task.get("workspace_id") or "arabian"
    persona = task.get("persona") or "others"

    req = OrchestrateRequest(
        user_message=prompt,
        coordinates=coords,
        session_id=session_id,
        onboarding_persona=persona,
        workspace_id=workspace_id
    )

    return run_orchestration(req)


async def _run_task(task: Dict[str, Any]):
    """Executes a single due task, updates SQLite transcript, and logs event."""
    task_id = task["task_id"]
    session_id = task["session_id"]
    prompt = task["prompt"]
    schedule_type = task["schedule_type"]
    interval_seconds = int(task.get("interval_seconds") or 0)

    try:
        session_store.mark_task_running(task_id)

        # Run orchestration in background thread pool to avoid blocking async loop
        result = await asyncio.to_thread(_execute_orchestration_sync, task)

        advisory_text = result.get("advisory") or "Scheduled oceanographic telemetry scan completed."
        summary = advisory_text[:120].strip() + ("..." if len(advisory_text) > 120 else "")

        # Compute next run if recurring
        next_run_at = None
        if schedule_type == "recurring" and interval_seconds > 0:
            next_run_at = (datetime.now(timezone.utc) + timedelta(seconds=interval_seconds)).isoformat()

        # Append assistant response directly into session's persistent SQLite transcript
        meta_info = {
            "scheduled": True,
            "task_id": task_id,
            "scheduled_prompt": prompt,
            "schedule_type": schedule_type,
            "telemetry": result.get("telemetry", {}),
            "hazard_status": result.get("hazard_status"),
            "agents_invoked": result.get("agents_invoked", [])
        }
        session_store.append_transcript_message(
            session_id=session_id,
            role="assistant",
            text=advisory_text,
            meta=meta_info,
            workspace_id=task.get("workspace_id", "arabian")
        )

        # Mark task completed or rescheduled
        session_store.complete_scheduled_task(
            task_id=task_id,
            summary=summary,
            payload=result,
            next_run_at=next_run_at
        )
        print(f"[Scheduler] Successfully executed task {task_id}: '{prompt[:40]}'")

    except Exception as exc:
        print(f"[Scheduler] Error executing task {task_id}: {exc}")
        # Mark completed so it doesn't loop fail forever
        session_store.complete_scheduled_task(
            task_id=task_id,
            summary=f"Execution error: {exc}",
            payload={"error": str(exc)},
            next_run_at=None
        )


async def scheduler_worker_loop():
    """Continuous background worker loop checking SQLite every 3 seconds for due tasks."""
    print("[Scheduler] Background scheduler loop started.")
    while True:
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            due_tasks = session_store.get_due_tasks(now_iso)
            for task in due_tasks:
                asyncio.create_task(_run_task(task))
        except Exception as e:
            print(f"[Scheduler] Worker loop error: {e}")
        await asyncio.sleep(3)


_worker_task: Optional[asyncio.Task] = None


def start_scheduler_service(app=None):
    """Starts the asyncio background task for the scheduler."""
    global _worker_task
    if _worker_task is None or _worker_task.done():
        try:
            loop = asyncio.get_running_loop()
            _worker_task = loop.create_task(scheduler_worker_loop())
        except RuntimeError:
            pass
