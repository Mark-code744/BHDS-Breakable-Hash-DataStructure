# BHDS — Breakable Hash Data Structure

> **Decoupled hash-pointer architecture for distributed trusted storage.**  
> Patent: CN122285666A — BHDS Breakable Hash & Pointer Decoupled Data Structure

## Overview

BHDS (Breakable Hash Data Structure) is a novel data architecture that decouples node hash (`h`) from predecessor pointer (`p`), enabling **O(1) single-point updates** while maintaining **Merkle-root-level verifiability**. Unlike traditional hash chains that require O(n) cascading updates, BHDS achieves constant-time local updates by isolating hash computation and pointer verification.

## Key Innovations

| Feature | Traditional Chain | BHDS |
|---------|-------------------|------|
| Single-point update | O(n) cascading | **O(1) local** |
| Hash-pointer coupling | Tight (prev_hash = f(prev_block)) | **Decoupled** |
| Global root update | Full rebuild | **O(log n) path-only** |
| Sub-chain verification | Not supported | **Break-and-rebuild** |

## Repository Structure

```
BHDS-Breakable-Hash-DataStructure/
├── BHDS.py                          # Exp 1: Single-point update latency
├── BHDS_rebuild.py                  # Exp 2: Break & rebuild timing
├── BHDS_Update.py                   # Exp 3: Global root update latency
├── Traditional Block List.py        # Baseline: Traditional hash chain (O(n))
├── Merkle Tree.py                   # Baseline: Standard Merkle tree
├── Merkle Tree Dynamic Merkle Tree.py # Baseline: Dynamic Merkle tree (cached layers)
├── Partitioned Merkle Tree.py       # Baseline: Partitioned Merkle tree (sharding)
└── Merkle DAG.py                    # Baseline: Merkle DAG
```

## Quick Start

### Requirements

```bash
pip install numpy pandas
```

### Run Experiments

```bash
# BHDS experiments
python BHDS.py
python BHDS_rebuild.py
python BHDS_Update.py

# Baseline comparisons
python "Traditional Block List.py"
python "Merkle Tree.py"
python "Merkle Tree Dynamic Merkle Tree.py"
python "Partitioned Merkle Tree.py"
python "Merkle DAG.py"
```

### Expected Output

Each experiment generates:
- `raw_*.csv` — Raw timing data per scale
- `summary_*.csv` — Statistical summary (mean, std, CI95, P95, P99)
- LaTeX table — Ready-to-use for academic papers

## Core Architecture

### BHDS Node (Five-Tuple)

```python
class BHDSNode:
    id: int        # Node identifier
    version: int   # Update counter
    data: str      # Payload
    h: str         # Self hash: H(id || version || data)
    p: str         # Pointer hash: H(prev_id || prev_h)
    prev: Node     # Backward link
    next: Node     # Forward link
```

### Update Flow

1. **Local Update** (O(1)): Modify `data` → recompute `h` → update successor's `p`
2. **Global Root** (O(log n)): Update leaf hash → propagate up Merkle path
3. **Break-and-Rebuild**: Snapshot sub-chain root → verify → restore integrity

## Experiment Design

| Experiment | Metric | Scales | Repeats |
|-----------|--------|--------|---------|
| Single-point update | Latency (ns) | 1K–200K | 30× |
| Break-and-rebuild | Break / Rebuild / Verify time (ns) | 100–1000 | 20× |
| Global root update | Local vs. global latency ratio | 1K–200K | 30× |
| Traditional chain | Baseline O(n) latency | 1K–200K | 30× |
| Merkle variants | Baseline O(log n) latency | 1K–200K | 30× |

## Hardware & Environment

- **CPU**: Intel Core i7-13700K @ 3.6GHz
- **RAM**: 16GB DDR4-3200
- **OS**: Windows 11 Pro 23H2 / Linux
- **Python**: 3.11.4
- **Hash**: SHA-256 (hashlib)

## Experimental Results

All raw timing data and statistical summaries are available in the `results/` directory.

| Directory | Contents |
|-----------|----------|
| `results/raw_*.csv` | 10 sets of raw timing data |
| `results/summary_*.csv` | 6 sets of statistical summaries |
| `results/README.md` | Detailed file index |

## Citation

If you use BHDS in your research, please cite:

```bibtex
@misc{bhds2024,
  title={BHDS: Breakable Hash Data Structure},
  author={Mark-code744},
  year={2024},
  howpublished={\url{https://github.com/Mark-code744/BHDS-Breakable-Hash-DataStructure}}
}
```

## Patents

1. CN122177292A — Mesh 2D Linked List for Periodic Table Construction
2. CN122196238A — Extensible General Mesh Topology Linked List
3. **CN122285666A — BHDS Breakable Hash & Pointer Decoupled Data Structure**
4. CN122311361A — NeuroChain Editable Neural-Blockchain Integrated System

## License

MIT License

## Contact

- Email: 3896456073@qq.com
- GitHub: [@Mark-code744](https://github.com/Mark-code744)
