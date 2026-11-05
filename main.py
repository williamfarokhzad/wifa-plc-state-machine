"""Offline scan-based conveyor model. No PLC or hardware connection."""
import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Inputs:
    start: bool = False
    stop: bool = False
    reset: bool = False
    part: bool = False
    permit: bool = True

    def __post_init__(self):
        if any(type(v) is not bool for v in vars(self).values()):
            raise ValueError("Every input must be a JSON boolean")

class Conveyor:
    def __init__(self, timeout_scans=5):
        if type(timeout_scans) is not int or not 1 <= timeout_scans <= 100000:
            raise ValueError("timeout_scans must be an integer from 1 to 100000")
        self.timeout_scans = timeout_scans
        self.state = "IDLE"
        self.age = 0
        self.scan = 0
        self.previous_start = False
        self.previous_reset = False

    def step(self, inputs):
        if not isinstance(inputs, Inputs):
            raise ValueError("step requires Inputs")
        start_edge = inputs.start and not self.previous_start
        reset_edge = inputs.reset and not self.previous_reset
        before = self.state
        reason = "hold"
        if not inputs.permit:
            self.state, reason = "FAULT", "permit_lost"
        elif inputs.stop:
            if self.state == "RUNNING":
                self.state, reason = "IDLE", "stop"
            else:
                reason = "stop_blocks_transition"
        elif self.state in ("FAULT", "COMPLETE"):
            if reset_edge:
                self.state, reason = "IDLE", "reset"
        elif self.state == "IDLE":
            if start_edge and not inputs.part:
                self.state, reason = "RUNNING", "start_edge"
            elif start_edge:
                reason = "part_blocks_start"
        elif self.state == "RUNNING":
            self.age += 1
            if inputs.part:
                self.state, reason = "COMPLETE", "part_detected"
            elif self.age >= self.timeout_scans:
                self.state, reason = "FAULT", "timeout"
        else:
            raise ValueError("Unknown internal state")
        if self.state != "RUNNING" or before != "RUNNING":
            self.age = 0
        self.previous_start = inputs.start
        self.previous_reset = inputs.reset
        self.scan += 1
        return {"scan": self.scan, "before": before, "state": self.state,
                "age_scans": self.age, "motor": self.state == "RUNNING",
                "reason": reason, **vars(inputs)}

def run_scenario(data):
    if set(data) != {"timeout_scans", "scan_ms", "scans"}:
        raise ValueError("Scenario needs timeout_scans, scan_ms and scans only")
    scan_ms = data["scan_ms"]
    if type(scan_ms) is not int or not 1 <= scan_ms <= 10000:
        raise ValueError("scan_ms must be an integer from 1 to 10000")
    scans = data["scans"]
    if not isinstance(scans, list) or not 1 <= len(scans) <= 10000:
        raise ValueError("scans must contain 1 to 10000 input objects")
    # Validate the whole trace before executing it. Missing inputs use defaults
    # on EACH scan; input values do not carry over between JSON rows.
    frames = []
    for frame in scans:
        if not isinstance(frame, dict) or set(frame) - set(Inputs.__dataclass_fields__):
            raise ValueError("Unknown input or non-object scan")
        frames.append(Inputs(**frame))
    machine = Conveyor(data["timeout_scans"])
    return [{**machine.step(frame), "time_ms": i * scan_ms}
            for i, frame in enumerate(frames)]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()
    try:
        rows = run_scenario(json.loads(args.scenario.read_text()))
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    if args.csv:
        try:
            args.csv.parent.mkdir(parents=True, exist_ok=True)
            with args.csv.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                writer.writeheader(); writer.writerows(rows)
        except OSError as exc:
            parser.error(f"Cannot write CSV output to {args.csv}: {exc}")
    print(json.dumps(rows, indent=2))

if __name__ == "__main__":
    main()
