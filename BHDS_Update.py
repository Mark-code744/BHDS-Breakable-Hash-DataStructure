import time
import hashlib
import random
import numpy as np
import pandas as pd

# ================================
# 固定随机种子
# ================================
RANDOM_SEED = 20240714
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

def sha256_hash(content):
    raw = str(content).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ================================
# BHDS节点
# ================================
class BHDSNode:
    __slots__ = ('id', 'version', 'data', 'h', 'p', 'prev', 'next')
    def __init__(self, id, data, prev_hash='0'*64):
        self.id = id
        self.version = 0
        self.data = data
        self.h = self.compute_hash()
        self.p = prev_hash
        self.prev = None
        self.next = None

    def compute_hash(self):
        s = f"{self.id}{self.version}{self.data}"
        return hashlib.sha256(s.encode()).hexdigest()


# ================================
# BHDS with Merkle Root
# ================================
class BHDSWithRoot:
    def __init__(self):
        self.head = None
        self.tail = None
        self.nodes = []
        self.node_count = 0
        self.leaves = []
        self.tree = []
        self.root = None
        self.leaf_padding = 0

    def add(self, id, data):
        prev_hash = self.tail.h if self.tail else '0'*64
        node = BHDSNode(id, data, prev_hash)
        if self.head is None:
            self.head = self.tail = node
        else:
            self.tail.next = node
            node.prev = self.tail
            self.tail = node
        self.nodes.append(node)
        self.node_count += 1
        # 只记录叶子哈希，不构建树
        leaf_hash = sha256_hash(f"{id}{node.version}{data}{node.p}")
        self.leaves.append(leaf_hash)

    def build_merkle_tree(self):
        """在所有节点添加完成后，构建一次Merkle树"""
        if not self.leaves:
            self.tree = []
            self.root = None
            return
        # 复制叶子
        current = self.leaves.copy()
        # 补全到2的幂（仅用于树构建，不改变self.leaves）
        n = len(current)
        if n & (n-1) != 0:
            target = 1 << (n.bit_length())
            last = current[-1]
            current += [last] * (target - n)
            self.leaf_padding = target - n
        else:
            self.leaf_padding = 0

        tree_levels = [current]
        while len(tree_levels[-1]) > 1:
            curr = tree_levels[-1]
            new_level = []
            for i in range(0, len(curr), 2):
                new_level.append(sha256_hash(curr[i] + curr[i+1]))
            tree_levels.append(new_level)
        self.tree = tree_levels
        self.root = self.tree[-1][0]

    def update_with_timing(self, node, new_data):
        """返回 (局部更新ns, 全局根更新ns)"""
        # ===== 局部更新 =====
        start_local = time.perf_counter_ns()
        node.data = new_data
        node.version += 1
        node.h = node.compute_hash()
        if node.next:
            node.next.p = node.h
        end_local = time.perf_counter_ns()
        local_time = end_local - start_local

        # ===== 全局根更新 =====
        start_global = time.perf_counter_ns()
        idx = self.nodes.index(node)
        # 更新实际叶子
        new_leaf = sha256_hash(f"{node.id}{node.version}{node.data}{node.p}")
        self.leaves[idx] = new_leaf
        # 更新树中的叶子（考虑补全，补全的叶子在最后）
        tree_idx = idx  # 因为补全只追加到末尾，实际索引不变
        self.tree[0][tree_idx] = new_leaf
        pos = tree_idx
        for depth in range(1, len(self.tree)):
            parent_idx = pos // 2
            left = self.tree[depth-1][2 * parent_idx]
            right = self.tree[depth-1][2 * parent_idx + 1]
            self.tree[depth][parent_idx] = sha256_hash(left + right)
            pos = parent_idx
        self.root = self.tree[-1][0]
        end_global = time.perf_counter_ns()
        global_time = end_global - start_global

        return local_time, global_time

    def get_random_node(self):
        return random.choice(self.nodes) if self.nodes else None


# ================================
# 单次测量
# ================================
def run_single_timing(scale, num_warmup=200, num_ops=20000):
    bhds = BHDSWithRoot()
    base_data = "X" * 100
    for i in range(scale):
        bhds.add(i, f"{base_data}_{i % 1000}")
    # 所有节点添加完成后构建一次Merkle树
    bhds.build_merkle_tree()

    # 预热
    for _ in range(num_warmup):
        node = bhds.get_random_node()
        if node:
            bhds.update_with_timing(node, f"{base_data}_{random.randint(0, 999)}")

    total_local = 0
    total_global = 0
    for _ in range(num_ops):
        node = bhds.get_random_node()
        if node:
            local_t, global_t = bhds.update_with_timing(node, f"{base_data}_{random.randint(0, 999)}")
            total_local += local_t
            total_global += global_t

    return total_local / num_ops, total_global / num_ops


# ================================
# 多组实验
# ================================
def run_root_update_benchmark(scales, repeats=30, num_warmup=200, num_ops=20000):
    all_results = {}
    for scale in scales:
        print(f"\n正在测试Root更新规模 {scale} ...")
        local_results = []
        global_results = []

        for rep in range(repeats):
            local_avg, global_avg = run_single_timing(scale, num_warmup, num_ops)
            local_results.append(local_avg)
            global_results.append(global_avg)
            if (rep + 1) % 10 == 0:
                print(f"  已完成 {rep + 1}/{repeats} 次重复")

        all_results[scale] = {
            'local_mean': np.mean(local_results),
            'local_std': np.std(local_results, ddof=1),
            'global_mean': np.mean(global_results),
            'global_std': np.std(global_results, ddof=1),
            'raw_local': local_results,
            'raw_global': global_results
        }
        print(f"  局部更新均值: {all_results[scale]['local_mean']:.0f} ns, "
              f"全局根更新均值: {all_results[scale]['global_mean']:.0f} ns")

    return all_results

def export_root_results(all_results, scales):
    # 原始数据
    raw_df = pd.DataFrame()
    for s in scales:
        raw_df[f"scale_{s}_local"] = all_results[s]['raw_local']
        raw_df[f"scale_{s}_global"] = all_results[s]['raw_global']
    raw_df.to_csv("raw_root_update_results.csv", index=False)
    print("\n原始数据已保存到 raw_root_update_results.csv")

    # 汇总表格
    summary_data = []
    for s in scales:
        r = all_results[s]
        summary_data.append({
            'scale': s,
            'local_mean_ns': r['local_mean'],
            'local_std_ns': r['local_std'],
            'global_mean_ns': r['global_mean'],
            'global_std_ns': r['global_std'],
            'ratio_global_to_local': r['global_mean'] / r['local_mean'] if r['local_mean'] > 0 else 0
        })
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv("summary_root_update_results.csv", index=False)
    print("统计汇总已保存到 summary_root_update_results.csv")

    # 打印表格
    print("\n" + "=" * 80)
    print("全局根更新时延统计结果")
    print("=" * 80)
    print(f"{'节点规模':<10} | {'局部更新均值(ns)':<18} | {'根更新均值(ns)':<18} | {'根/局部比例'}")
    print("-" * 80)
    for s in scales:
        r = all_results[s]
        print(f"{s:<10} | {r['local_mean']:<18.0f} | {r['global_mean']:<18.0f} | {r['global_mean']/r['local_mean']:.2f}x")
    print("=" * 80)


# ================================
# 主程序
# ================================
if __name__ == "__main__":
    scales = [1000, 10000, 50000, 100000, 200000]
    repeats = 30
    num_warmup = 200
    num_ops = 20000

    print("=" * 80)
    print("BHDS 全局Root更新时间实验")
    print(f"  节点规模: {scales}")
    print(f"  重复次数: {repeats}")
    print(f"  每次操作数: {num_ops}")
    print("=" * 80)

    all_results = run_root_update_benchmark(scales, repeats, num_warmup, num_ops)
    export_root_results(all_results, scales)

    print("\n实验完成！")