"""Static regression checks for source-level runtime invariants.

These tests intentionally avoid importing PySide6 or the MuMu API, so they can
run on a clean CI worker and catch accidental source regressions.
"""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "gps_controller_qt.py"
TEXT = SOURCE.read_text(encoding="utf-8")
TREE = ast.parse(TEXT, filename=str(SOURCE))


def find_class(name: str) -> ast.ClassDef:
    return next(node for node in TREE.body if isinstance(node, ast.ClassDef) and node.name == name)


def find_method(class_node: ast.ClassDef, name: str) -> ast.FunctionDef:
    return next(node for node in class_node.body if isinstance(node, ast.FunctionDef) and node.name == name)


def called_attributes(node: ast.AST) -> set[str]:
    return {
        child.func.attr
        for child in ast.walk(node)
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
    }


class SourceInvariantTests(unittest.TestCase):
    def test_source_compiles(self):
        compile(TEXT, str(SOURCE), "exec")

    def test_first_run_manual_coordinates_have_no_demo_location(self):
        gps_tab = find_method(find_class("GPSWindow"), "_build_gps_tab")
        self.assertNotIn("35.6812", ast.unparse(gps_tab))
        self.assertNotIn("139.7671", ast.unparse(gps_tab))
        self.assertIn("self.last_manual_location", ast.unparse(gps_tab))

    def test_first_run_route_has_two_empty_rows(self):
        route_tab = ast.unparse(find_method(find_class("GPSWindow"), "_build_route_tab"))
        self.assertIn('["", ""]', route_tab)
        self.assertNotIn("35.6812,139.7671", route_tab)

    def test_route_history_does_not_mark_all_stops_as_visited(self):
        record_route = find_method(find_class("GPSWindow"), "_record_route")
        self.assertNotIn("_record_location", called_attributes(record_route))

    def test_route_worker_records_only_successful_emitted_stops(self):
        worker = find_class("Worker")
        self.assertIn("record_route", {n.targets[0].id for n in worker.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)})
        launch = ast.unparse(find_method(find_class("GPSWindow"), "_launch_route"))
        self.assertIn("worker.record_route.emit(points)", launch)
        self.assertIn("worker.record_location.emit(end[0], end[1], "路线行走")", launch)

    def test_shutdown_waits_for_threads_asynchronously(self):
        gps_window = find_class("GPSWindow")
        poll = ast.unparse(find_method(gps_window, "_poll_workers_before_close"))
        close = ast.unparse(find_method(gps_window, "closeEvent"))
        self.assertIn("isRunning", poll)
        self.assertIn("QTimer.singleShot", poll)
        self.assertIn("QTimer.singleShot", close)

    def test_api_false_or_empty_result_is_not_treated_as_success(self):
        backend = find_class("MumuBackend")
        send = ast.unparse(find_method(backend, "_send_to_instance"))
        broadcast = ast.unparse(find_method(backend, "broadcast_location"))
        self.assertIn("if not result", send)
        self.assertIn("if result:", broadcast)


if __name__ == "__main__":
    unittest.main()
