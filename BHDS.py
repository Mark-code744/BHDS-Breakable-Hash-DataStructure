import hashlib
import time
import random
import numpy as np
import pandas as pd
import os

# ================================
# 固定随机种子
# ================================
RANDOM_SEED = 20240714
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# ================================
# BHDS 核心数据结构
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
        # h_i = H(id || version || data)
        s = f"{self.id}{self.version}{self.data}"
        return hashlib.sha256(s.encode()).hexdigest()

class BHDS:
    def __init__(self):
        self.head = None
        self.tail = None
        self.nodes = []
        self.node_count = 0

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

    def update(self, node, new_data):
        # 更新当前节点：数据、版本、哈希
        node.data = new_data
        node.version += 1
        node.h = node.compute_hash()
        # 更新后继节点的前驱指针（O(1)）
        if node.next:
            node.next.p = node.h

    def get_random_node(self):
        return random.choice(self.nodes) if self.nodes else None


# ================================
# 单次实验函数
# ================================
def run_single_benchmark(scale, num_warmup=200, num_ops=20000):
    """对指定规模执行一次完整的测量，返回单次更新操作的平均耗时（ns）"""
    # 1. 构建链表
    bhds = BHDS()
    # 数据长度固定为100字节
    base_data = "X" * 100
    for i in range(scale):
        bhds.add(i, f"{base_data}_{i % 1000}")

    # 2. 预热
    for _ in range(num_warmup):
        node = bhds.get_random_node()
        if node:
            # 模拟数据更新（修改部分内容，而非完全替换）
            new_data = f"{base_data}_{random.randint(0, 999)}"
            bhds.update(node, new_data)

    # 3. 正式测量
    start = time.perf_counter_ns()
    for _ in range(num_ops):
        node = bhds.get_random_node()
        if node:
            new_data = f"{base_data}_{random.randint(0, 999)}"
            bhds.update(node, new_data)
    end = time.perf_counter_ns()

    return (end - start) / num_ops   # 平均耗时（ns）


# ================================
# 多组实验主程序
# ================================
def run_multi_benchmark(scales, repeats=30, num_warmup=200, num_ops=20000):
    """对多个规模进行多组重复实验，返回完整的统计结果"""
    all_results = {}

    for scale in scales:
        print(f"\n正在测试规模 {scale} ...")
        results = []

        for rep in range(repeats):
            avg_ns = run_single_benchmark(scale, num_warmup, num_ops)
            results.append(avg_ns)
            if (rep + 1) % 10 == 0:
                print(f"  已完成 {rep + 1}/{repeats} 次重复")

        # 统计结果
        mean = np.mean(results)
        std = np.std(results, ddof=1)
        sem = std / np.sqrt(repeats)
        ci_95 = 1.96 * sem
        p95 = np.percentile(results, 95)
        p99 = np.percentile(results, 99)

        all_results[scale] = {
            'mean': mean,
            'std': std,
            'sem': sem,
            'ci_95': ci_95,
            'p95': p95,
            'p99': p99,
            'min': min(results),
            'max': max(results),
            'raw': results
        }

        print(f"  均值: {mean:.0f} ns, 标准差: {std:.0f} ns, 95%置信区间: ±{ci_95:.0f} ns")

    return all_results


# ================================
# 导出数据函数
# ================================
def export_results(all_results, scales, filename="bhds_benchmark_results.csv"):
    """导出完整的统计结果和原始数据"""
    # 1. 导出原始数据（每个规模一列）
    raw_df = pd.DataFrame()
    for s in scales:
        raw_df[f"scale_{s}"] = all_results[s]['raw']
    raw_df.to_csv(f"raw_{filename}", index=False)
    print(f"\n原始数据已保存到 raw_{filename}")

    # 2. 导出统计汇总
    summary_data = []
    for s in scales:
        r = all_results[s]
        summary_data.append({
            'scale': s,
            'mean_ns': r['mean'],
            'std_ns': r['std'],
            'sem_ns': r['sem'],
            'ci_95_ns': r['ci_95'],
            'p95_ns': r['p95'],
            'p99_ns': r['p99'],
            'min_ns': r['min'],
            'max_ns': r['max'],
            'repeats': len(r['raw'])
        })
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(f"summary_{filename}", index=False)
    print(f"统计汇总已保存到 summary_{filename}")

    # 3. 打印LaTeX格式表格
    print("\n" + "=" * 80)
    print("LaTeX 表格（可直接复制到论文）")
    print("=" * 80)
    print("\\begin{table}[htbp]")
    print("\\centering")
    print("\\caption{BHDS单点更新时延统计结果}")
    print("\\begin{tabular}{|r|r|r|r|r|r|}")
    print("\\hline")
    print("节点规模 & 均值 (ns) & 标准差 (ns) & 95\\% CI & P95 (ns) & 重复次数 \\\\")
    print("\\hline")
    for s in scales:
        r = all_results[s]
        print(f"{s} & {r['mean']:.0f} & {r['std']:.0f} & $\\pm${r['ci_95']:.0f} & {r['p95']:.0f} & {len(r['raw'])} \\\\")
    print("\\hline")
    print("\\end{tabular}")
    print("\\end{table}")

    # 4. 打印本文档的代码信息
    print("\n" + "=" * 80)
    print("实验配置信息")
    print("=" * 80)
    print(f"""
实验配置：
- 硬件: Intel Core i7-13700K @ 3.6GHz, 16GB DDR4-3200
- 操作系统: Windows 11 Pro 23H2
- Python版本: 3.11.4
- 哈希函数: SHA-256 (hashlib实现)
- 节点数据长度: 100 字节
- 每次测量操作数: 20000
- 预热次数: 200
- 重复次数: {repeats}
- 随机种子: {RANDOM_SEED}
- 测量工具: time.perf_counter_ns()
- 统计方法: 样本标准差 (ddof=1), 95%置信区间 (正态近似)
""")


# ================================
# 主程序
# ================================
if __name__ == "__main__":
    # 可配置参数
    scales = [1000, 10000, 50000, 100000, 200000]
    repeats = 30
    num_warmup = 200       # 预热次数
    num_ops = 20000        # 每次测量的操作数

    print("=" * 80)
    print("BHDS 实验数据生成（真实测量）")
    print(f"  节点规模: {scales}")
    print(f"  每组重复次数: {repeats}")
    print(f"  每次测量操作数: {num_ops}")
    print(f"  随机种子: {RANDOM_SEED}")
    print("=" * 80)

    all_results = run_multi_benchmark(scales, repeats, num_warmup, num_ops)

    # 导出所有结果
    export_results(all_results, scales)

    print("\n" + "=" * 80)
    print("实验完成！")
    print("=" * 80)