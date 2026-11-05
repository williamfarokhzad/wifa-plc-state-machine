# PLC state machine: an offline conveyor lab

Run a deterministic Python model of a PLC-style sequence. Follow one state transition per scan, replay normal and abnormal input traces, and test restart behavior. This is original educational software. It has no PLC driver and controls no machine.

Full canonical lesson: https://wifarobotics.com/learn/plc-state-machine/

## Start from zero

Install Python 3.10 or newer from https://www.python.org/downloads/. On Windows enable the Python launcher. Open this repository's green Code menu, choose Download ZIP and extract it. Open a terminal in the extracted folder containing main.py. Check `python --version`. If unavailable, use `py` on Windows or `python3` on Linux/macOS in every command below. Git users may clone this repository instead of downloading the ZIP.

```sh
python main.py examples/normal.json --csv results/normal.csv
python main.py examples/timeout.json --csv results/timeout.csv
python main.py examples/stop-restart.json --csv results/stop-restart.csv
python -m unittest discover -s tests -v
```

No pip dependencies, account, PLC IDE or hardware are needed. The fifteen test methods should pass. Commands print JSON rows and save CSV files that you can open in a spreadsheet. Run from the project root so tests can import main. Results are overwritten only at the explicit --csv path; use another path to keep a previous experiment.

## Read a scan

Each JSON object in `scans` is one input snapshot. Omitted values revert to their defaults on every scan: start, stop, reset and part are false; permit is true. A value from a previous row does not carry forward. Inputs must be real JSON booleans, not 0, 1 or strings. Unknown input names are rejected.

Each row reports the state before and after the transition, simulated time in ms, motor Boolean, running age in scans, and transition reason. The first snapshot is at time zero. Inputs are sampled, one transition is selected, then motor is computed from the resulting state. RUNNING means motor=true; every other state means motor=false. No wall-clock sleep is used.

## Transition contract

| Priority | Condition | Result |
| --- | --- | --- |
| 1 | permit=false in any state | FAULT, motor off |
| 2 | stop=true while RUNNING | IDLE, motor off |
| 2 | stop=true in any other state | Hold state; block start/reset |
| 3 | FAULT or COMPLETE and fresh reset edge | IDLE, motor off |
| 4 | IDLE, fresh start edge and no part | RUNNING, age=0 |
| 4 | IDLE and part=true | Start is blocked |
| 5 | RUNNING and part=true | COMPLETE, motor off |
| 6 | RUNNING reaches timeout without part | FAULT, motor off |

Other combinations hold the current state. A rising edge means true now and false in the previous snapshot, including snapshots where a higher-priority rule blocked the command. A held reset during permit loss must be released and pressed again after permit returns. Reset never starts a run in the same scan. COMPLETE and FAULT latch until accepted reset, except permit loss changes COMPLETE to FAULT. A stop returns to IDLE and discards progress; it is not a pause.

Timeout is the number of subsequent RUNNING scans, excluding the scan that enters RUNNING. With 100 ms scans and timeout_scans=5, a run started at 100 ms faults at 600 ms when the sensor stays false. Sensor detection at that exact deadline wins over timeout. This ordering is our teaching contract, not a universal PLC rule. age_scans resets to zero outside RUNNING, so the FAULT row shows zero; the reason still reports timeout.

## Expected results

normal: IDLE, RUNNING, RUNNING, COMPLETE, IDLE, RUNNING. Motor values: false, true, true, false, false, true. The final row deliberately starts a second run.

timeout: IDLE, RUNNING, RUNNING, RUNNING, RUNNING, RUNNING, FAULT, IDLE. Timeout occurs at 600 ms.

stop-restart: RUNNING, IDLE, IDLE, IDLE, RUNNING, FAULT, FAULT, FAULT, IDLE, RUNNING. A held start cannot restart after stop. Permit loss forces a latched fault. A reset while permit=false does not clear it.

## Make an experiment

Copy an example JSON file and edit only the copy. Set timeout_scans to 3 and run again. The deadline should move earlier by two scan intervals. Add part=true at the deadline: expect COMPLETE. Add stop=true in the same row: expect IDLE because stop has higher priority. Set permit=false there as well: expect FAULT. Keep start=true across a stop and observe that no fresh start edge exists. Release it for a scan, then press again to start.

## Tests and troubleshooting

Tests cover exact normal trace and output values, timeout boundary, simultaneous sensor/stop/permit conditions, blocked and held commands, latched completion, reset sequencing, invalid data and timestamp semantics. The exhaustive two-scan check tries all 1,024 pairs of the 32 Boolean input snapshots and asserts output invariants. It is bounded testing, not a proof over every possible execution. Three CLI tests also compare every CSV field with JSON output, check nested output creation and confirm that invalid output paths preserve existing files and directories.

If Python is missing, reopen the terminal after installation or use the interpreter alias above. If tests cannot import main, change to the project root. If a JSON error appears, check commas, quotes and lowercase true/false. If a sensor disappears unexpectedly, remember omitted inputs reset to defaults each row. If a spreadsheet locks a CSV, close it or choose another --csv path. A stuck FAULT usually means permit is still false or reset has no fresh rising edge.

## Fix a CSV output error

If the command reports `Cannot write CSV output to`, read the destination and operating system error in the message. Give `--csv` a file path such as `results/normal.csv`, not an existing directory. Every parent component must be a directory; an existing file named `results` cannot contain `normal.csv`. Close a spreadsheet that locks the file, or choose a writable destination. Quote paths containing spaces.

CSV output errors exit with code 2 and do not print a successful JSON trace. Successful commands create missing parent directories. Writing is not atomic: an error after a regular output file is opened can leave it truncated or partially written. Keep valuable results at a separate path and inspect the exit code before using a new trace.

## Simulation boundaries

Python models discrete control decisions only. scan_ms is a label for a fixed simulated interval, not measured execution time. This is not a PLC runtime, IEC 61131-3 conformance implementation, vendor project, compiled Structured Text, or validated timer function block. Real task scheduling, jitter, bus update timing, input filtering, startup retention, motor feedback, contactors, braking and sensor faults are absent. The permit Boolean is an ordinary process condition. It is not an emergency stop, guard circuit or safety function. Do not connect this code to moving equipment.

For a later PLC port, define task interval and I/O update order, map states to an enum and CASE, choose vendor timer and edge blocks, and repeat tests in the target simulator. That port and hardware commissioning are outside this repository's validation.

## Primary references

CODESYS documentation explains [CASE branches](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_st_instruction_case.html), [task configuration and timing](https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_f_reference_task.html) and the [Standard library](https://content.helpme-codesys.com/en/libs/Standard/Current/index.html). These inform the concepts; the transition priorities above are specific to our original model.

Python documents [CSV file handling](https://docs.python.org/3.12/library/csv.html) and [command line error reporting](https://docs.python.org/3.12/library/argparse.html#argparse.ArgumentParser.error).

Original implementation by WIFA Robotics. No license grant is implied; contact the owner for reuse permission.
