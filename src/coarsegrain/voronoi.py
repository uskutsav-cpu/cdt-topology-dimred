"""Graph-distance sampling and connected Voronoi cells in any dimension.

Annulus sampling follows section 4.1 of arXiv:2510.05695v1. The explicit tie
rule below is uniform over labels reachable through already colored previous-
layer neighbors, guaranteeing connected cells. It is not claimed to reproduce
an unpublished author's random-number stream or all-nearest-seed tie law.
"""
from collections import deque
from dataclasses import dataclass
from numbers import Integral
import numpy as np


def checked_graph(graph):
    if not graph:
        raise ValueError('empty graph')
    if any(isinstance(v, bool) or not isinstance(v, Integral) for v in graph):
        raise ValueError('integer vertex IDs required')
    g = {}
    for v, neighbors in graph.items():
        row = tuple(neighbors)
        if any(isinstance(u, bool) or not isinstance(u, Integral) for u in row):
            raise ValueError('integer neighbor IDs required')
        if len(set(row)) != len(row) or v in row:
            raise ValueError('simple graph required')
        g[int(v)] = tuple(sorted(map(int, row)))
    for v, row in g.items():
        if any(u not in g or v not in g[u] for u in row):
            raise ValueError('graph must be undirected and closed on its vertex set')
    return g


def distances(graph, roots, cutoff=None):
    roots = tuple(roots)
    if not roots or any(v not in graph for v in roots):
        raise ValueError('nonempty roots must belong to graph')
    out = {v: 0 for v in roots}
    todo = deque(roots)
    while todo:
        v = todo.popleft()
        if cutoff is not None and out[v] >= cutoff:
            continue
        for u in graph[v]:
            if u not in out:
                out[u] = out[v] + 1
                todo.append(u)
    return out


def poisson_seeds(graph, delta, seed):
    g = checked_graph(graph)
    if isinstance(delta, bool) or not isinstance(delta, Integral) or delta < 1:
        raise ValueError('delta must be a positive integer')
    if len(distances(g, [min(g)])) != len(g):
        raise ValueError('paper sampler requires a connected graph')
    rng = np.random.default_rng(seed)
    sampled, active, covered = [], [], set()
    def add(v):
        sampled.append(v)
        active.append(v)
        covered.update(distances(g, [v], delta - 1))
    add(int(rng.choice(sorted(g))))
    while active:
        i = int(rng.integers(len(active)))
        v = active.pop(i)
        annulus = {u for u, d in distances(g, [v], 2 * delta - 1).items()
                   if d >= delta}
        while annulus - covered:
            add(int(rng.choice(sorted(annulus - covered))))
    if covered != set(g):
        raise RuntimeError('annulus sampling failed to cover the graph')
    return tuple(sampled)


@dataclass(frozen=True)
class Partition:
    seeds: tuple
    labels: dict
    distances: dict
    parents: dict
    tie_rule: str = 'layerwise_uniform_reachable_label'


def voronoi(graph, seeds, seed):
    g = checked_graph(graph)
    seeds = tuple(seeds)
    if (not seeds or len(set(seeds)) != len(seeds)
            or any(isinstance(v, bool) or not isinstance(v, Integral) or v not in g for v in seeds)):
        raise ValueError('seeds must be distinct graph vertices')
    dist = distances(g, seeds)
    if len(dist) != len(g):
        raise ValueError('every connected component needs a seed')
    layers = {}
    for v, d in dist.items():
        layers.setdefault(d, []).append(v)
    rng = np.random.default_rng(seed)
    labels = {v: i for i, v in enumerate(seeds)}
    parents = {v: v for v in seeds}
    for d in range(1, max(dist.values()) + 1):
        for v in sorted(layers[d]):
            previous = [u for u in g[v] if dist[u] == d - 1]
            choices = sorted({labels[u] for u in previous})
            label = int(rng.choice(choices))
            labels[v] = label
            parents[v] = min(u for u in previous if labels[u] == label)
    return Partition(seeds, labels, dist, parents)


def validate_partition(graph, partition, delta=None):
    g = checked_graph(graph)
    if set(partition.labels) != set(g) or set(partition.parents) != set(g):
        raise ValueError('partition does not cover exactly the graph')
    shortest = distances(g, partition.seeds)
    if shortest != partition.distances:
        raise ValueError('incorrect nearest-seed distances')
    for v in g:
        c = partition.labels[v]
        if not isinstance(c, Integral) or not 0 <= c < len(partition.seeds):
            raise ValueError('invalid cell label')
        root = partition.seeds[c]
        parent = partition.parents[v]
        if v == root:
            if parent != v or shortest[v] != 0:
                raise ValueError('invalid root')
        elif (parent not in g[v] or partition.labels[parent] != c
              or shortest[parent] != shortest[v] - 1):
            raise ValueError('cell lacks a shortest same-label parent path')
    minimum = None
    if len(partition.seeds) > 1:
        minimum = min(distances(g, [v])[u] for i, v in enumerate(partition.seeds)
                      for u in partition.seeds[i + 1:])
    coverage = max(shortest.values())
    if delta is not None and (coverage >= delta or (minimum is not None and minimum < delta)):
        raise ValueError('sampling separation/coverage contract failed')
    return {'vertices': len(g), 'seeds': len(partition.seeds),
            'coverage_radius': coverage, 'minimum_seed_distance': minimum,
            'connected_cells': True, 'tie_rule': partition.tie_rule}
