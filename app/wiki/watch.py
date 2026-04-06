"""Stdlib polling watch service for wiki rebuilds."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Event, Lock, Thread
import time

from app.wiki.service import WikiBuildResult, WikiService


@dataclass(slots=True)
class WatchState:
    workspace_id: str
    running: bool
    last_built_at: str | None = None
    last_error: str | None = None


class WikiWatchService:
    def __init__(self, wiki_service: WikiService) -> None:
        self.wiki = wiki_service
        self._threads: dict[str, Thread] = {}
        self._stops: dict[str, Event] = {}
        self._states: dict[str, WatchState] = {}
        self._lock = Lock()

    def start(self, workspace_id: str) -> WatchState:
        config = self.wiki.update_vault(workspace_id, watcher_enabled=True)
        initial_built_at = None
        initial_error = None
        try:
            result = self.wiki.scan_and_build(workspace_id)
            initial_built_at = result.generated_at
        except Exception as exc:
            initial_error = str(exc)
        with self._lock:
            if workspace_id in self._threads and self._threads[workspace_id].is_alive():
                return self._states[workspace_id]
            stop = Event()
            thread = Thread(target=self._run, args=(workspace_id, config.watch_interval_seconds, stop), daemon=True)
            self._threads[workspace_id] = thread
            self._stops[workspace_id] = stop
            self._states[workspace_id] = WatchState(
                workspace_id=workspace_id,
                running=True,
                last_built_at=initial_built_at,
                last_error=initial_error,
            )
            thread.start()
            return self._states[workspace_id]

    def stop(self, workspace_id: str) -> WatchState:
        with self._lock:
            stop = self._stops.get(workspace_id)
            if stop is not None:
                stop.set()
            state = self._states.get(workspace_id, WatchState(workspace_id=workspace_id, running=False))
            state.running = False
            self._states[workspace_id] = state
        self.wiki.update_vault(workspace_id, watcher_enabled=False)
        return self._states[workspace_id]

    def status(self, workspace_id: str) -> WatchState:
        with self._lock:
            return self._states.get(workspace_id, WatchState(workspace_id=workspace_id, running=False))

    def _run(self, workspace_id: str, interval_seconds: float, stop: Event) -> None:
        previous_files: dict[str, str] = {}
        while not stop.wait(interval_seconds):
            try:
                result = self.wiki.scan_and_build(workspace_id)
                current_files = self.wiki.page_index(workspace_id).get("files", {})
                if current_files != previous_files:
                    previous_files = current_files
                with self._lock:
                    self._states[workspace_id] = WatchState(
                        workspace_id=workspace_id,
                        running=True,
                        last_built_at=result.generated_at,
                        last_error=None,
                    )
            except Exception as exc:
                with self._lock:
                    self._states[workspace_id] = WatchState(
                        workspace_id=workspace_id,
                        running=True,
                        last_built_at=self._states.get(workspace_id, WatchState(workspace_id, True)).last_built_at,
                        last_error=str(exc),
                    )
