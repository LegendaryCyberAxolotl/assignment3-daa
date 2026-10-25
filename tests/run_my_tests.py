"""Own tests. Run from the repository root:  python tests/run_my_tests.py

1. hand-derived cases from tests/my_cases.json (checked with the public validator)
2. the validator accepts another valid answer and rejects wrong ones
3. the route helper, called directly
4. state reset: mixed requests, repeated, through the real main.py process
5. large inputs and deep chains with analytically known answers
"""
import json
import pathlib
import random
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src" / "Python"))

import algorithms
import main
from public_validate import check

failures = 0


def report(ok, name, extra=""):
    global failures
    if not ok:
        failures += 1
    print(("PASS " if ok else "FAIL ") + name + (("  " + extra) if extra else ""))


# --- 1. hand-derived cases --------------------------------------------------
print("== 1. hand-derived cases ==")
cases = json.load(open(ROOT / "tests" / "my_cases.json", encoding="utf-8"))
for case in cases:
    answer = main.handle(case["input"])
    report(check(case["input"], answer, case["output"]), case["name"], json.dumps(answer))

# --- 2. validator accepts alternatives, rejects wrong answers ---------------
print("== 2. validator sanity: other valid answer accepted, wrong answer rejected ==")
tie = {"task": "kruskal", "n": 3, "edges": [[0, 1, 1], [1, 2, 1], [0, 2, 1]]}
expected = {"cost": 2, "edge_ids": [0, 1], "components": 1}
report(check(tie, {"cost": 2, "edge_ids": [1, 2], "components": 1}, expected),
       "accepts a different optimal forest [1,2]")
report(not check(tie, {"cost": 2, "edge_ids": [0, 1, 2], "components": 1}, expected),
       "rejects a forest with a cycle (3 edges)")
report(not check(tie, {"cost": 3, "edge_ids": [0, 1], "components": 1}, expected),
       "rejects a wrong cost")
diamond = {"task": "topo", "n": 4, "edges": [[0, 1], [0, 2], [1, 3], [2, 3]]}
good = {"acyclic": True, "order": [0, 1, 2, 3]}
report(check(diamond, {"acyclic": True, "order": [0, 2, 1, 3]}, good), "topo: accepts order 0,2,1,3")
report(not check(diamond, {"acyclic": True, "order": [3, 2, 1, 0]}, good), "topo: rejects reversed order")
scc_in = {"task": "scc", "n": 3, "edges": [[0, 1], [1, 0], [1, 2]]}
scc_good = {"component": [0, 0, 1], "condensation": [[0, 1]]}
report(check(scc_in, {"component": [9, 9, 4], "condensation": [[9, 4]]}, scc_good), "scc: accepts other labels")
report(not check(scc_in, {"component": [0, 1, 2], "condensation": [[0, 2], [1, 2]]}, scc_good),
       "scc: rejects wrong grouping")
dag_in = {"task": "dag", "n": 3, "source": 0, "edges": [[0, 1, 5], [0, 1, 2], [1, 2, 1], [0, 2, 3]]}
dag_good = {"acyclic": True, "distance": [0, 2, 3], "parent_edge": [-1, 1, 2]}
report(check(dag_in, {"acyclic": True, "distance": [0, 2, 3], "parent_edge": [-1, 1, 3]}, dag_good),
       "dag: accepts the tied parent edge 3")
report(not check(dag_in, {"acyclic": True, "distance": [0, 2, 3], "parent_edge": [-1, 0, 2]}, dag_good),
       "dag: rejects parent edge with the wrong weight")

# --- 3. route helper called directly ----------------------------------------
print("== 3. route helper ==")


def route_cost(route, parent_edge, edges):
    """Walk the route, check edge direction and return the total weight."""
    total = 0
    for previous, current in zip(route, route[1:]):
        start, end, weight = edges[parent_edge[current]]
        assert (start, end) == (previous, current), "edge direction mismatch"
        total += weight
    return total


readme = {"task": "dag", "n": 5, "source": 0,
          "edges": [[0, 1, 3], [0, 2, 8], [1, 2, -7], [2, 3, 4]]}
result = algorithms.dag(readme)
edges, parent_edge, distance = readme["edges"], result["parent_edge"], result["distance"]
route = algorithms.restore_route(0, 3, parent_edge, edges)
report(route == [0, 1, 2, 3] and route_cost(route, parent_edge, edges) == distance[3] == 0,
       "reachable target 3", f"route={route}, edge ids={[parent_edge[v] for v in route[1:]]}, cost={distance[3]}")
route = algorithms.restore_route(0, 0, parent_edge, edges)
report(route == [0], "route to the source itself", f"route={route}")
route = algorithms.restore_route(0, 4, parent_edge, edges)
report(route is None, "unreachable target 4 -> None", f"route={route}")

result = algorithms.dag(dag_in)
edges, parent_edge, distance = dag_in["edges"], result["parent_edge"], result["distance"]
for target in (1, 2):
    route = algorithms.restore_route(0, target, parent_edge, edges)
    cost = route_cost(route, parent_edge, edges)
    report(cost == distance[target], f"parallel/tied edges, target {target}",
           f"route={route}, edge ids={[parent_edge[v] for v in route[1:]]}, cost={cost}")

# --- 4. state reset ----------------------------------------------------------
print("== 4. state reset (real main.py process, same batch twice) ==")
mixed = [c["input"] for c in cases]
payload = "".join(json.dumps(r) + "\n" for r in mixed + mixed)
completed = subprocess.run([sys.executable, str(ROOT / "src" / "Python" / "main.py")],
                           input=payload, capture_output=True, text=True, timeout=20)
lines = [json.loads(line) for line in completed.stdout.splitlines()]
half = len(mixed)
report(len(lines) == 2 * half and completed.returncode == 0, "one answer per request, exit code 0")
report(all(check(r, a, c["output"]) for r, a, c in zip(mixed + mixed, lines, cases + cases)),
       "all answers valid in both batches")
report(lines[:half] == lines[half:], "second batch identical to the first (no leaked state)")

# --- 5. large inputs ----------------------------------------------------------
print("== 5. large inputs / deep chains ==")
N, M = 100_000, 250_000


def timed(label, request, verify):
    start = time.perf_counter()
    answer = main.handle(request)
    seconds = time.perf_counter() - start
    report(verify(answer), label, f"{seconds:.2f}s")
    return answer


rng = random.Random(2026)
ops = [[i, i + 1] for i in range(N - 1)] + [[rng.randrange(N), rng.randrange(N)] for _ in range(M - (N - 1))]
timed("dsu: chain n=100000 + random, q=250000", {"task": "dsu", "n": N, "operations": ops},
      lambda a: len(a["states"]) == M and a["states"][N - 2] == [1, N] and a["states"][-1] == [1, N]
      and all(a["states"][k] == [N - 1 - k, k + 2] for k in range(0, N - 1, 997)))

chain = [[i, i + 1] for i in range(N - 1)]
timed("topo: chain 100000 (order is forced: 0..n-1)", {"task": "topo", "n": N, "edges": chain},
      lambda a: a["acyclic"] and a["order"] == list(range(N)))
timed("topo: chain closed into a cycle", {"task": "topo", "n": N, "edges": chain + [[N - 1, 0]]},
      lambda a: a == {"acyclic": False, "order": []})
timed("scc: one big cycle -> a single component",
      {"task": "scc", "n": N, "edges": chain + [[N - 1, 0]]},
      lambda a: len(set(a["component"])) == 1 and a["condensation"] == [])
timed("scc: chain -> n components, n-1 condensation edges", {"task": "scc", "n": N, "edges": chain},
      lambda a: len(set(a["component"])) == N and len(a["condensation"]) == N - 1)
timed("dag: chain, weight -1 each: distance[i] = -i",
      {"task": "dag", "n": N, "source": 0, "edges": [[i, i + 1, -1] for i in range(N - 1)]},
      lambda a: a["acyclic"] and a["distance"] == [-i for i in range(N)]
      and a["parent_edge"] == [-1] + list(range(N - 1)))

rnd = [[rng.randrange(N), rng.randrange(N), rng.randint(-10**9, 10**9)] for _ in range(M)]
kr = timed("kruskal: random n=100000 m=250000", {"task": "kruskal", "n": N, "edges": rnd}, lambda a: True)
pr = timed("prim: same graph, same cost and components, valid forest",
           {"task": "prim", "n": N, "edges": rnd},
           lambda a: check({"task": "prim", "n": N, "edges": rnd}, a, kr))
report(check({"task": "kruskal", "n": N, "edges": rnd}, kr, pr), "kruskal forest valid against prim's cost")

print("\nFAILED:", failures) if failures else print("\nALL OK")
sys.exit(1 if failures else 0)
