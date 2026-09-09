"""Native-compatible seed geometry, not a sample from an equilibrated ensemble.

The oriented 18-tetrahedron slab is the pattern of JorenB/3d-cdt's pinned
example/geometries/sample-g0-T3.cdt. It can be periodically repeated at any T>=3.
Generic combinatorial validity does NOT guarantee the native driver's ordering
conventions; the actual native move/export tests are required as well.
"""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import numpy as np
from geometry import Geometry, write_geometry

SLAB = np.array([
    [0,1,2,5],[1,2,5,7],[1,5,6,7], [0,3,1,5],[3,1,5,6],[3,5,8,6],
    [0,2,3,5],[2,3,5,8],[2,5,7,8], [4,2,1,9],[2,1,9,7],[1,9,7,6],
    [4,1,3,9],[1,3,9,6],[3,9,6,8], [4,3,2,9],[3,2,9,8],[2,9,8,7]], dtype=np.int64)


def seed_geometry(time_extent: int) -> Geometry:
    if type(time_extent) is not int or not 3 <= time_extent <= 4096:
        raise ValueError('time_extent must be an integer in [3,4096]')
    tetra = np.concatenate([np.where(SLAB < 5, SLAB + 5*t,
                            SLAB - 5 + 5*((t+1) % time_extent)) for t in range(time_extent)])
    incidence = defaultdict(list)
    for i, cell in enumerate(tetra):
        for k in range(4):
            incidence[tuple(sorted(np.delete(cell, k)))].append((i,k))
    neighbors = np.full_like(tetra, -1)
    for pairs in incidence.values():
        if len(pairs) != 2:
            raise ArithmeticError('seed face does not have two incident tetrahedra')
        (i,k),(j,l) = pairs
        neighbors[i,k], neighbors[j,l] = j,i
    return Geometry(np.repeat(np.arange(time_extent),5),tetra,neighbors,True)


def write_seed(time_extent: int, path: Path) -> dict:
    from .geometry import validate_geometry
    g = seed_geometry(time_extent)
    report = validate_geometry(g)
    if path.exists():
        from geometry import read_geometry
        old = read_geometry(path)
        if not all(np.array_equal(getattr(old,k),getattr(g,k)) for k in ('time','tetra','neighbors')):
            raise ValueError('existing seed differs')
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        write_geometry(g,path)
    return report
