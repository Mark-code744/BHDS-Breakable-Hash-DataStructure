# BHDS — Breakable Hash Data Structure

> **Decoupled hash-pointer architecture for distributed trusted storage.**  
> Reproducibility artifacts for *"A Breakable Hash Data Structure and Its Verification Mechanism for Dynamic Ledger States"*.  
> Patent: CN122285666A — BHDS Breakable Hash & Pointer Decoupled Data Structure

## Repository Structure

```
BHDS-Breakable-Hash-DataStructure/
├── python/                          # Main experiments (Table 3–7, 9–12)
│   ├── BHDS.py                      # Exp 1: Single-point update latency
│   ├── BHDS_rebuild.py              # Exp 2: Break & rebuild timing
│   ├── BHDS_Update.py               # Exp 3: Global root update latency
│   ├── Traditional Block List.py    # Baseline: Traditional hash chain (O(n))
│   ├── Merkle Tree.py               # Baseline: Standard Merkle tree
│   ├── Merkle Tree Dynamic Merkle Tree.py  # Baseline: Dynamic Merkle tree
│   ├── Partitioned Merkle Tree.py   # Baseline: Partitioned Merkle tree
│   └── Merkle DAG.py                # Baseline: Merkle DAG
├── cpp/                             # Cross-language validation (Table 8)
│   ├── src/benchmark.cpp            # C++17 re-implementation
│   ├── CMakeLists.txt               # Build configuration
│   └── README.md                    # Build & run instructions
└── results/                         # Raw experimental data
```

## Quick Start

### Python Experiments (Primary)

```bash
pip install numpy pandas

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

### C++ Validation (Table 8)

```bash
cd cpp
cmake -B build
cmake --build build
./build/benchmark
```

> **Note**: C++ code uses a self-contained SHA-256 implementation (no OpenSSL). Absolute latencies differ from Python, but asymptotic trends (O(1) vs O(n) vs O(log n)) are consistent across languages.

## Core Architecture

### BHDS Node (Five-Tuple)

```python
class BHDSNode:
    id: int        # Node identifier
    version: int   # Update counter
    data: str      # Payload
    h: str         # Self hash: H(id || version || data)
    p: str         # Pointer hash: H(prev_id || prev_h)
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
| **C++ cross-validation** | Single-point latency | 1K–200K | 5-run trimmed mean |

## Hardware & Environment

- **CPU**: Intel Core i7-13700K @ 3.6GHz
- **RAM**: 16GB DDR4-3200
- **OS**: Windows 11 Pro 23H2 / Linux
- **Python**: 3.11.4
- **C++**: C++17 (GCC/Clang/MSVC)
- **Hash**: SHA-256

## Results

All raw timing data and statistical summaries are available in the `results/` directory.

## Citation

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
