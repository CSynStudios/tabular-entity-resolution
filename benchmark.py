import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

import psutil


def benchmark(input_path, output_directory):
    output_directory = Path(output_directory)
    if output_directory.exists():
        raise ValueError("Benchmark output directory already exists.")
    output_directory.mkdir(parents=True)
    command = [sys.executable, str(Path(__file__).with_name("clean_table.py")), "--input", str(Path(input_path).resolve()), "--output", str((output_directory / "run").resolve())]
    started = time.perf_counter()
    child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    observed = psutil.Process(child.pid)
    peak_rss = 0
    while child.poll() is None:
        try:
            peak_rss = max(peak_rss, observed.memory_info().rss)
        except psutil.NoSuchProcess:
            break
        time.sleep(0.05)
    stdout, stderr = child.communicate()
    if child.returncode:
        raise RuntimeError(stderr.strip() or stdout.strip() or f"Cleaner exited with {child.returncode}")
    report = json.loads((output_directory / "run/report.json").read_text(encoding="utf-8"))
    measurements = {"summary": report["summary"], "wall_seconds": round(time.perf_counter() - started, 6), "sampled_peak_rss_mib": round(peak_rss / 1_048_576, 3), "rss_sample_interval_seconds": 0.05}
    (output_directory / "benchmark.json").write_text(json.dumps(measurements, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(measurements, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Measure a separate cleaner process, including sampled resident memory.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        benchmark(arguments.input, arguments.output)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"Benchmark failed: {error}\n")


if __name__ == "__main__":
    main()
