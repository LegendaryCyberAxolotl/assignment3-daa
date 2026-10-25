"""Graph algorithms for the festival-preparation assignment.

Every function receives the parsed JSON request (a dict) and returns a dict.
All state is created inside the functions, so nothing leaks between requests.
All DFS traversals are iterative (explicit stack), so deep graphs are safe.
"""

import heapq

def dsu(request):
    """DSU with path compression and union by size/rank; return states."""
    n = request["n"]
    operations = request["operations"]

    parent = list(range(n))

    size = [1] * n
    component_count = n
    largest_component = 1 if n > 0 else 0
    states = []

    def find_root(vertex):
        root = vertex

        while parent[root] != root:
            root = parent[root]

        while parent[vertex] != root:
            next_vertex = parent[vertex]
            parent[vertex] = root
            vertex = next_vertex

        return root

    for first_vertex, second_vertex in operations:
        big_root = find_root(first_vertex)
        small_root = find_root(second_vertex)

        if big_root != small_root:

            if size[big_root] < size[small_root]:
                big_root, small_root = small_root, big_root

            parent[small_root] = big_root
            size[big_root] += size[small_root]
            component_count -= 1
            largest_component = max(largest_component, size[big_root])

        states.append([component_count, largest_component])

    return {"states": states}

def kruskal(request):
    """Separate Kruskal implementation; return cost, edge_ids, components."""
    n = request["n"]
    edges = request["edges"]

    parent = list(range(n))
    size = [1] * n

    def find_root(vertex):
        root = vertex
        while parent[root] != root:
            root = parent[root]

        while parent[vertex] != root:
            next_vertex = parent[vertex]
            parent[vertex] = root
            vertex = next_vertex

        return root
    
    edge_ids_by_weight = sorted(range(len(edges)), key=lambda edge_id: edges[edge_id][2])

    total_cost = 0
    chosen_edge_ids = []

    for edge_id in edge_ids_by_weight:
        start, end, weight = edges[edge_id]
        start = find_root(start)
        end = find_root(end)

        if start == end:
            continue

        if size[start] < size[end]:
            start, end = end, start

        parent[end] = start
        size[start] += size[end]
        total_cost += weight
        chosen_edge_ids.append(edge_id)

    return {
        "cost": total_cost,
        "edge_ids": chosen_edge_ids,
        "components": n - len(chosen_edge_ids),
    }

def prim(request):
    """Separate Prim implementation; restart for every unvisited component."""
    n = request["n"]
    edges = request["edges"]

    neighbours = [[] for _ in range(n)]
    for edge_id, (start, end, weight) in enumerate(edges):
        neighbours[start].append((weight, edge_id, end))
        neighbours[end].append((weight, edge_id, start))

    visited = [False] * n
    total_cost = 0
    chosen_edge_ids = []
    component_count = 0

    for root in range(n):

        if visited[root]:
            continue

        component_count += 1
        visited[root] = True
        heap = list(neighbours[root])
        heapq.heapify(heap)

        while heap:
            weight, edge_id, new_vertex = heapq.heappop(heap)
            if visited[new_vertex]:
                continue

            visited[new_vertex] = True
            total_cost += weight
            chosen_edge_ids.append(edge_id)

            for item in neighbours[new_vertex]:
                if not visited[item[2]]:
                    heapq.heappush(heap, item)

    return {"cost": total_cost, "edge_ids": chosen_edge_ids, "components": component_count}

def scc(request):
    """Kosaraju with two DFS passes; return component and condensation."""
    n = request["n"]
    edges = request["edges"]

    forward = [[] for _ in range(n)]
    backward = [[] for _ in range(n)]
    for start, end in edges:
        forward[start].append(end)
        backward[end].append(start)

    visited = [False] * n
    next_neighbour = [0] * n
    finish_order = []

    for root in range(n):
        if visited[root]:
            continue

        visited[root] = True
        stack = [root]
        while stack:
            vertex = stack[-1]
            if next_neighbour[vertex] < len(forward[vertex]):
                neighbour = forward[vertex][next_neighbour[vertex]]
                next_neighbour[vertex] += 1

                if not visited[neighbour]:
                    visited[neighbour] = True
                    stack.append(neighbour)

            else:
                finish_order.append(vertex)
                stack.pop()

    component = [-1] * n
    label_count = 0

    for root in reversed(finish_order):
        if component[root] != -1:
            continue

        component[root] = label_count
        stack = [root]
        while stack:
            vertex = stack.pop()

            for neighbour in backward[vertex]:
                if component[neighbour] == -1:
                    component[neighbour] = label_count
                    stack.append(neighbour)

        label_count += 1

    pairs = set()
    for start, end in edges:
        if component[start] != component[end]:
            pairs.add((component[start], component[end]))

    return {"component": component, "condensation": [list(pair) for pair in pairs]}

def _topological_order(n, edges):
    """Return a topological order, or None if the graph has a directed cycle.

    Only the first two items of every edge (start, end) are used, so edges with
    a weight in third position are fine.
    """
    neighbours = [[] for _ in range(n)]
    for edge in edges:
        neighbours[edge[0]].append(edge[1])

    NOT_VISITED, ACTIVE, FINISHED = 0, 1, 2

    state = [NOT_VISITED] * n
    next_neighbour = [0] * n
    finish_order = []

    for root in range(n):
        if state[root] != NOT_VISITED:
            continue

        state[root] = ACTIVE
        stack = [root]

        while stack:
            vertex = stack[-1]
            if next_neighbour[vertex] < len(neighbours[vertex]):
                neighbour = neighbours[vertex][next_neighbour[vertex]]
                next_neighbour[vertex] += 1

                if state[neighbour] == ACTIVE:
                    return None
                
                if state[neighbour] == NOT_VISITED:
                    state[neighbour] = ACTIVE
                    stack.append(neighbour)

            else:
                state[vertex] = FINISHED
                finish_order.append(vertex)
                stack.pop()

    finish_order.reverse()
    return finish_order


def topo(request):
    """Three-state DFS and reverse finish order; return acyclic and order."""
    order = _topological_order(request["n"], request["edges"])

    if order is None:
        return {"acyclic": False, "order": []}
    
    return {"acyclic": True, "order": order}

def dag(request):
    """Whole-graph cycle check and DAG relaxation; add your own route helper."""
    n = request["n"]
    source = request["source"]
    edges = request["edges"]

    order = _topological_order(n, edges)
    if order is None:
        return {"acyclic": False, "distance": [], "parent_edge": []}

    outgoing = [[] for _ in range(n)]
    for edge_id, (start, end, weight) in enumerate(edges):
        outgoing[start].append((end, weight, edge_id))

    distance = [None] * n
    parent_edge = [-1] * n
    distance[source] = 0

    for vertex in order:
        if distance[vertex] is None:
            continue

        for end, weight, edge_id in outgoing[vertex]:
            candidate = distance[vertex] + weight
            if distance[end] is None or candidate < distance[end]:
                distance[end] = candidate
                parent_edge[end] = edge_id

    return {"acyclic": True, "distance": distance, "parent_edge": parent_edge}


def restore_route(source, target, parent_edge, edges):
    """Return the vertex list from source to target, following parent_edge IDs.

    Result for an unreachable target: None (the empty list is a valid route to
    nothing, None makes "no route" explicit and cannot be confused with a path).
    A route to the source itself is [source].
    """
    if target != source and parent_edge[target] == -1:
        return None
    
    route = [target]
    vertex = target

    while vertex != source:
        vertex = edges[parent_edge[vertex]][0]
        route.append(vertex)
        
    route.reverse()
    return route
