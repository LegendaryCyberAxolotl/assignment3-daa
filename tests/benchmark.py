"""Kruskal vs Prim on identical graphs.  Run from the repository root:

    python tests/benchmark.py

Timed region: one call algorithms.kruskal(request) / algorithms.prim(request), measured with
time.perf_counter(). It INCLUDES everything the function does itself (sorting / building the
adjacency lists / heap work / DSU) and EXCLUDES graph generation, JSON parsing and output.
Both methods get the same in-memory request and the same timing boundaries.
One untimed warm-up call per method and size, then 5 timed calls; the median is reported.
"""
import platform
import random
import statistics
import sys
import time
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src" / "Python"))

import algorithms
from public_validate import check

SEED = 2026
SIZES = [(1_000, 4_000), (10_000, 40_000), (100_000, 250_000)]
RUNS = 5


def cpu_name():
    try:
        for line in open("/proc/cpuinfo", encoding="utf-8"):
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
            
    except OSError:
        pass

    return platform.processor() or "unknown"


def median_seconds(function, request):
    function(request)
    samples = []

    for _ in range(RUNS):
        start = time.perf_counter()
        function(request)
        samples.append(time.perf_counter() - start)

    return samples, statistics.median(samples)


print(f"Python {platform.python_version()} on {platform.platform()}")
print(f"CPU: {cpu_name()}")
print(f"seed={SEED}, weights uniform in [-10^9, 10^9], endpoints uniform (loops/parallel edges possible)")
print(f"{RUNS} timed runs after 1 warm-up; timer: time.perf_counter()\n")

for n, m in SIZES:
    rng = random.Random(SEED + n)
    edges = [[rng.randrange(n), rng.randrange(n), rng.randint(-10**9, 10**9)] for _ in range(m)]
    request = {"n": n, "edges": edges}
    kruskal_answer = algorithms.kruskal(request)
    prim_answer = algorithms.prim(request)
    same = (kruskal_answer["cost"] == prim_answer["cost"]
            and kruskal_answer["components"] == prim_answer["components"])
    valid = (check({"task": "kruskal", **request}, kruskal_answer, prim_answer)
             and check({"task": "prim", **request}, prim_answer, kruskal_answer))
    print(f"n={n}, m={m}: cost={kruskal_answer['cost']}, components={kruskal_answer['components']}, "
          f"costs equal={same}, both forests valid={valid}")
    for name, function in (("kruskal", algorithms.kruskal), ("prim", algorithms.prim)):
        samples, median = median_seconds(function, request)
        print(f"  {name:8s} runs(s)={[round(s, 4) for s in samples]}  median={median:.4f}s")
    print()
