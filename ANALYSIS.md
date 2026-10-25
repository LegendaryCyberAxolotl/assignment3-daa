# Assignment 3 — Analysis (Python)

Language: Python 3.10 (standard library only, no build step).
Files: `src/Python/algorithms.py` (all six methods + `restore_route`), `src/Python/main.py` (supplied adapter, unchanged),
`tests/` (own tests), `submission.json` (`{"language":"Python"}`).

## 0. Commands

```terminal
python tools/run.py --setup
python tools/run.py --check
python tools/run.py --input tests/my_cases.jsonl
python tests/run_my_tests.py | tee tests/results.txt
python tests/benchmark.py   | tee tests/benchmark_results.txt
```

## 1. Sources, AI tools and my own verification

**AI assistance.** The AI (Claude) was used for assistance to figure out the logic, how it should work and for debugging purposes and small optimizasions like `sorted(range(len(edges)), key=lambda edge_id: edges[edge_id][2])`. It was also used to generate the scripts for creating and running tests. All the algorythm logic was made by me. Claude was also used to assist in writing the ANALYSIS.md. Especially to translate my thoughts into a more technical language.

**My own verification.** I tested my code with the assistance of Claude and ran the tests on my pc to make sure everything work as it was supposed to.

- I ran `benchmark.py` and `run_my_tests.py` myself to create text documents with resuls.

## 2. Cross-cutting design

**State reset.** Every function builds all of its arrays (`parent_of`, `neighbours`, `visited`, ...) from scratch inside
the call. There are no module-level mutable variables, no caches and no default-argument lists, so one request cannot
influence the next. Verified by running the full batch twice in one process (`tests/run_my_tests.py`, section 4, and
`python tools/run.py --check`, the "state reset" line).

**Deep DFS.** Python's recursion limit (about 1000 frames) would break on a chain of 100000 vertices, so every traversal
uses an explicit stack. For the three-state DFS (`topo`, `dag`) and the first Kosaraju pass the stack holds vertices and a
separate array `next_neighbour[v]` stores the position of the next unexamined neighbour of `v`. When a vertex returns to the
top of the stack, the scan resumes there instead of starting over, so each edge is examined exactly once (O(n+m), not
O(n·deg)). The pointer is advanced *before* descending to the neighbour. Chains of 100000 vertices run in 0.03–0.25 s
(section 5). The second Kosaraju pass only needs to collect everything reachable, so a plain stack with `pop()` is enough.

**Edge IDs.** The ID of `edges[i]` is `i`. Kruskal sorts the *list of IDs* by weight rather than the edges, so IDs survive
sorting. Prim and the DAG relaxation store the ID inside the adjacency entries.

**Integers.** Python integers are unbounded, so sums of up to 250000 weights of magnitude 10^9 (about 2.5·10^14) cannot
overflow. Unreachable distances are `None`, which `json.dumps` writes as `null`.

## 3. Methods

### 3.1 `dsu`
*Steps.* Create `parent` (each vertex is its own root) and `size`. For each operation find both roots. If they differ,
attach the root of the smaller tree under the root of the larger one, add the sizes, decrease `component_count`, update
`largest_component`. Append `[component_count, largest_component]` after **every** operation, including no-op ones.

*Invariant.* The vertices of every tree are exactly one connected component; `component_count` equals the number of roots;
`tree[r]` is correct for every root `r`; `largest_component` is the maximum of `tree` over all roots.

*Correctness.* A union of two vertices in the same tree changes no component, and `[u,u]` finds the same root twice, so both
are no-ops. A real union merges exactly two components, so the count falls by 1; the largest component can only change if it is
the new merged one, hence `max(old, new size)` suffices. `find_root` is iterative: first pass finds the root, second pass
re-hangs every vertex of the path directly under it (path compression).

*Edge cases.* `n=0` gives `largest=0` and no operations, so `states=[]`; `n>0` starts with `largest=1`; no operations gives `[]`.

*Complexity.* Time O(n + q·α(n)) amortized (union by size + path compression); memory O(n + q) including `states`.

### 3.2 `kruskal`
*Steps.* Sort edge IDs by weight; scan them in order with its own DSU (a separate implementation, not shared with `dsu`);
accept an edge iff its endpoints have different roots. `components = n - (accepted edges)`.

*Invariant.* The accepted edges form a forest that is contained in some minimum spanning forest, and the DSU components are
the connected components of that forest.

*Correctness.* The cheapest remaining edge that connects two different components is a light edge across the cut
(component, rest), hence safe by the cut property. Edges inside one component would close a cycle and are skipped, which also
removes self-loops and all but the best parallel edge. Negative weights do not matter, the argument only compares weights. A
forest with `c` components over `n` vertices has exactly `n - c` edges.

*Edge cases.* `n=0`: cost 0, no IDs, 0 components. Isolated vertices are components. Ties: sorting is stable, any optimum is
accepted.

*Complexity.* Time O(n + m log m) (the sort dominates), memory O(n + m).

### 3.3 `prim`
*Steps.* Build adjacency lists with entries `(weight, edge_id, other_end)` (every edge in both lists). For each unvisited
vertex start a new tree: mark it visited, heapify its edges. Pop the lightest entry; if its far end is already visited discard
it (lazy deletion), otherwise accept the edge, mark the vertex and push its edges that lead to unvisited vertices. When the
heap is empty the component is complete; the outer loop moves to the next unvisited vertex. `components` counts the restarts.

*Invariant.* The visited set of the current tree is connected by accepted edges; the heap contains every edge leaving it
(plus stale entries that lead back inside).

*Correctness.* The lightest non-stale heap entry is a lightest edge across the cut (visited, unvisited) inside this component,
safe by the cut property. Each restart handles one connected component, so the union is a spanning forest. Self-loops lead to an
already visited vertex and are always discarded.

*Edge cases.* As for Kruskal; additionally the restart is what makes disconnected graphs and isolated vertices work.

*Complexity.* Time O(n + m log m) with the lazy heap (up to 2m entries, log(2m) = O(log m)); memory O(n + m).

### 3.4 `scc` (Kosaraju)
*Steps.* Build the graph and its transpose. Pass 1: iterative DFS over the original graph from every unvisited vertex,
recording vertices in finishing order. Pass 2: take vertices in **decreasing** finishing order; each unlabelled one starts a DFS
on the transposed graph that labels everything it reaches (and that is unlabelled) with a new label. Condensation: for every
edge between vertices with different labels add the pair (label(u), label(v)) to a set.

*Invariant.* When pass 2 starts a search at vertex `r`, all components found so far are complete and `r` has the latest
finishing time among the remaining vertices.

*Correctness.* Key lemma: if there is an edge from component C to a different component C', the latest finishing time in C is
later than the latest in C'. Therefore the vertex with the latest remaining finishing time lies in a *source* component of the
remaining condensation. In the transposed graph that component is a *sink*, so the search from `r` can only reach `r`'s own
component, and it reaches all of it (mutual reachability is preserved by transposition). Repeating this peels off one component per
launch. The condensation set contains each ordered pair once and never contains inner edges or self-loops.

*Edge cases.* Isolated vertices get their own label; duplicates and self-loops are harmless; `n=0` gives two empty arrays.

*Complexity.* Time O(n + m) expected (hash set for pairs), memory O(n + m).

### 3.5 `topo` (three-state DFS)
*Steps.* Adjacency lists; state per vertex: not visited / active (on the stack) / finished. Iterative DFS from every unvisited
vertex using `next_neighbour`. An edge into an **active** vertex means a directed cycle: return `acyclic=false, order=[]`. An
edge into a finished vertex is ignored. When a vertex's neighbours are exhausted it becomes finished and is appended to the
finish list. If no cycle was found the reversed finish list is the order.

*Invariant.* The active vertices are exactly the vertices on the current DFS stack, and form a path of edges.

*Correctness.* An edge `u -> v` into an active `v` closes the path `v -> u -> v`, which is a cycle. Conversely, if a cycle exists,
the first of its vertices to be reached makes DFS reach the rest while it is still active, so some edge of the cycle hits an
active vertex. In an acyclic graph every edge `u -> v` finishes `v` before `u` (v is either finished already or is explored while u
is active), so the reversed finish order puts `u` before `v`.

*Edge cases.* A self-loop is an edge into an active vertex, hence a cycle. Parallel edges are harmless. A cycle in a part of
the graph with no connection to the rest is found because DFS starts from every vertex. `n=0` returns `acyclic=true, order=[]`.

*Complexity.* Time O(n + m), memory O(n + m).

### 3.6 `dag` (shortest paths in a DAG)
*Steps.* Run the same cycle check/ordering as `topo` on the **whole** graph (shared helper `_topological_order`; weights in
the third position are ignored). If a cycle exists anywhere, return `acyclic=false` and empty arrays. Otherwise set
`distance[source]=0`, everything else `None`, `parent_edge=-1`. Go through the topological order; skip vertices whose distance
is `None`; relax each outgoing edge, and on improvement store the new distance and the **edge ID**.

*Invariant.* When vertex `u` is processed, `distance[u]` is final (it equals the shortest path length, or `None` if
unreachable).

*Correctness.* In a topological order every edge entering `u` comes from a vertex processed earlier, and each of those already
relaxed its edges, so `distance[u]` is already the minimum over all incoming edges. Negative weights do not break this because no
vertex is ever revisited. Relaxing from `None` is skipped, since "infinity + weight" would be meaningless (and `-1` cannot be
used as a marker for unreachable, because it can be a real distance). Following `parent_edge` backwards ends at the source
because every parent edge starts at a vertex that was reached earlier in the order.

*Edge cases.* A cycle unreachable from the source still gives `acyclic=false`; a self-loop is a cycle; parallel edges and ties
yield any valid parent edge; the source has `parent_edge=-1`; `n=1` works.

*Complexity.* Time O(n + m), memory O(n + m).

### 3.7 Route helper `restore_route(source, target, parent_edge, edges)`
Walks from `target` backwards: take `parent_edge[v]`, move to that edge's start vertex, repeat until the source is reached, then
reverse. For `target == source` the result is `[source]`. **For an unreachable target it returns `None`** (an empty list could be
mistaken for a path; `None` states "no route"). The `distance` array in the JSON still uses `null` for unreachable. Time and
memory O(L) for a route of L vertices.

## 4. Test inventory

`tests/my_cases.json` holds 20 hand-derived cases (each with an explanation in the `why` field), `tests/my_cases.jsonl` is the
same inputs for `tools/run.py --input`, `tests/run_my_tests.py` runs everything and `tests/results.txt` is its saved output.
Expected answers were derived by reasoning on small graphs, not copied from program output. Categories: empty and disconnected
graphs, isolated vertices, repeated unions and unions with itself, self-loops, parallel edges and tied optima, negative
weights, sums above 32 bits, unreachable vertices (including a genuine distance of −1), cycles outside the source's reach, a
diamond (a finished vertex reached twice is not a cycle), and large and deep inputs.

## 5. Results of my own tests (from `tests/results.txt`)

All checks pass. Highlights:

- 20/20 hand-derived cases pass.
- The checker accepts a different optimal forest (`[1,2]` instead of `[0,1]`), another topological order, other SCC labels and
  the other tied parent edge, and **rejects** a forest with a cycle, a wrong cost, a reversed order, a wrong SCC grouping and a
  parent edge with the wrong weight.
- A mixed batch of all 20 requests, sent twice through the real `main.py` process, produced identical answers in both halves.
- Large inputs (n=100000, m or q up to 250000), single run, this machine: DSU 0.26 s; topo on a chain 0.10 s (order forced to
  `0..n−1`) and 0.14 s with the closing edge (cycle detected); SCC on one big cycle 0.25 s and on a chain 0.62 s; DAG chain with
  weight −1 (`distance[i] = −i`) 0.27 s; Kruskal on a random graph 0.40 s, Prim 1.07 s with equal cost and components.

## 6. Real route-helper calls

Graph from the README: `n=5, source=0, edges = [[0,1,3],[0,2,8],[1,2,-7],[2,3,4]]`,
`distance=[0,3,-4,0,null]`, `parent_edge=[-1,0,2,3,-1]`.

| Call | Result | Edge IDs used | Check |
|---|---|---|---|
| `restore_route(0, 3, ...)` reachable | `[0,1,2,3]` | `[0,2,3]` | edges 0→1, 1→2, 2→3 in forward direction; 3 + (−7) + 4 = 0 = `distance[3]` |
| `restore_route(0, 0, ...)` source | `[0]` | none | route to the source is `[source]` |
| `restore_route(0, 4, ...)` unreachable | `None` | none | `distance[4]` is `null`, no route |

Parallel and tied edges: `n=3, source=0, edges=[[0,1,5],[0,1,2],[1,2,1],[0,2,3]]` gives `distance=[0,2,3]`,
`parent_edge=[-1,1,3]`.

| Call | Result | Edge IDs used | Check |
|---|---|---|---|
| target 1 | `[0,1]` | `[1]` | the cheaper parallel edge (weight 2, not the weight 5 one); cost 2 = `distance[1]` |
| target 2 | `[0,2]` | `[3]` | tie: direct edge costs 3, the path 0→1→2 (IDs 1, 2) also costs 3; the helper follows the stored parent; cost 3 = `distance[2]` |

## 7. Edge cases that are handled by design

Empty graph (`n=0`) in DSU/Kruskal/Prim/SCC/topo; isolated vertices; self-loops (never chosen by MST, a cycle for
topo/dag, never in a condensation); parallel and duplicate edges; negative weights; ties; sums beyond 32 bits; unreachable
vertices and the difference between `null` and −1; cycle outside the reachable part; deep chains; repeated requests.

## 8. Kruskal vs Prim

**Setup.** `python tests/benchmark.py` (output in `tests/benchmark_results.txt`). Python 3.10.5, Windows
(`platform.platform()`: Windows-10-10.0.26200-SP0), AMD64 Family 23 Model 96 Stepping 1, AuthenticAMD.
AMD Ryzen 7 4800H with Radeon Graphycs
Graphs are generated with `random.Random(2026 + n)`: endpoints uniform (self-loops and parallel edges possible), weights uniform
in [−10^9, 10^9]. **Both methods run on the identical graph object.**
Timer: `time.perf_counter()` around one call of `algorithms.kruskal(request)` / `algorithms.prim(request)`. The timed region
includes what the function does itself (sorting, building adjacency lists, heap/DSU work). It excludes graph generation, JSON
parsing and output; both methods use the same boundaries. One untimed warm-up call, then 5 timed calls; median reported. No
compilation is involved. Before timing, the benchmark checks that both methods give the same cost and number of components and that
both forests are valid (via the public validator): all three sizes passed.

| n | m | components | cost | Kruskal runs (s) | Kruskal median | Prim runs (s) | Prim median |
|---:|---:|---:|---:|---|---:|---|---:|
| 1,000 | 4,000 | 2 | −698,691,434,917 | 0.0036, 0.0044, 0.0038, 0.0058, 0.0052 | **0.0044 s** | 0.0137, 0.0074, 0.0063, 0.0057, 0.0053 | **0.0063 s** |
| 10,000 | 40,000 | 10 | −7,053,881,511,518 | 0.0495, 0.0475, 0.0436, 0.0407, 0.0426 | **0.0436 s** | 0.1020, 0.0971, 0.1102, 0.1193, 0.1003 | **0.1020 s** |
| 100,000 | 250,000 | 692 | −53,143,143,777,730 | 0.4389, 0.4309, 0.4140, 0.4444, 0.4771 | **0.4389 s** | 1.0782, 1.0762, 1.0628, 1.0425, 1.0421 | **1.0628 s** |

**Observations.** Both are correct and agree on cost and components. In this implementation Kruskal is faster at every size:
about 1.4× at n=1,000, 2.3× at n=10,000 and 2.4× at n=100,000 (ratio of medians). From n=10,000 to 100,000 the input grows 10× in
vertices and 6.25× in edges, while the time grows about 10.1× (Kruskal) and 10.4× (Prim). The m·log m term alone would predict
roughly 7.3×; the observed growth is somewhat higher, which is compatible with the linear n term (Python allocates several
arrays of n elements per call) and with worse cache behaviour on larger arrays, although I did not separate these effects.
The smallest size is the least reliable: runs take only a few milliseconds, the spread between runs is large (Kruskal 0.0036–0.0058 s;
the first Prim run, 0.0137 s, is about twice the others, cause not investigated), and the median is used precisely so that
such outliers do not matter.

**Interpretation.** Asymptotically both are O(n + m log m) (lazy-heap Prim), so the theory predicts similar growth, and the
measurement agrees on growth but not on the constant. A likely reason (consistent with the operation counts, but I did **not**
profile it): Kruskal does one sort of m integers with a C-level key (the sort runs inside the interpreter's C code) and then
roughly 2m cheap `find` calls, while Prim first builds 2m adjacency tuples and then performs up to 2m heap pushes and pops of
tuples whose comparisons are more expensive. In a compiled language the gap would probably be smaller or differently shaped.

**Limitations.** Only random sparse graphs (m/n between 2.5 and 4) were tested; dense graphs, where an indexed-heap Prim
usually looks better, were not. A single machine (Windows, laptop, power settings were not controlled: with opened browser, mains power supply),
5 repetitions, one seed per size. The ratio m/n differs between sizes, so the three rows are not a pure scaling experiment. The Python
version, the lazy-deletion design of Prim and tuple-based heap entries influence the constant factors. These results should be read as
"this implementation on these graphs", not as a general ranking of the algorithms.