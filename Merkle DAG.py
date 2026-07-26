import time
import hashlib
import random
import numpy as np
import pandas as pd
import statistics
import math

# ================================
# 固定随机种子
# ================================
RANDOM_SEED = 20240714
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

def precise_time():
    return time.perf_counter_ns()

def sha256_hash(content):
    raw = str(content).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ====================== Merkle DAG类 ======================
class MerkleDAG:
    def __init__(self, data_list):
        self.nodes = dict()    # 全局哈希缓存：hash→原始值/父子对
        self.layers = []       # 分层缓存，保存每一层完整哈希列表
        self.leaves = []
        # 初始化叶子
        for d in data_list:
            h = sha256_hash(d)
            self.leaves.append(h)
            self.nodes[h] = d
        self.layers.append(self.leaves.copy())
        self._build_full_tree()
        self.root = self.layers[-1][0]

    def _build_full_tree(self):
        curr = self.layers[-1].copy()
        while len(curr) > 1:
            if len(curr) % 2 != 0:
                curr.append(curr[-1])
            new_layer = []
            for i in range(0, len(curr), 2):
                pair = (curr[i], curr[i+1])
                combine = curr[i] + curr[i+1]
                ph = sha256_hash(combine)
                self.nodes[pair] = ph
                new_layer.append(ph)
            self.layers.append(new_layer)
            curr = new_layer

    def update_node(self, leaf_idx, new_val):
        # 1 更新目标叶子
        new_h = sha256_hash(new_val)
        self.leaves[leaf_idx] = new_h
        self.nodes[new_h] = new_val
        self.layers[0][leaf_idx] = new_h
        pos = leaf_idx
        # 2 只向上更新单条路径，复用缓存
        for depth in range(1, len(self.layers)):
            parent_pos = pos // 2
            l_idx = parent_pos * 2
            r_idx = parent_pos * 2 + 1
            l_h = self.layers[depth-1][l_idx]
            r_h = self.layers[depth-1][r_idx]
            new_p = sha256_hash(l_h + r_h)
            self.layers[depth][parent_pos] = new_p
            self.nodes[(l_h, r_h)] = new_p
            pos = parent_pos
        self.root = self.layers[-1][0]


# ====================== 统计工具 ======================
def calc_95ci(data_list):
    n = len(data_list)
    std = statistics.stdev(data_list)
    ci = 1.96 * std / math.sqrt(n)
    return round(ci)

def calc_p95(data_list):
    sorted_data = sorted(data_list)
    p95_pos = int(len(sorted_data) * 0.95)
    if p95_pos >= len(sorted_data):
        p95_pos = len(sorted_data) - 1
    return round(sorted_data[p95_pos])


# ====================== 单次实验函数 ======================
def run_single_benchmark(scale, num_warmup=200, num_ops=20000):
    """对指定规模执行一次完整的测量，返回单次更新操作的平均耗时（ns）"""
    # 1. 构建Merkle DAG
    data = [f"Block_{i}" for i in range(scale)]
    dag = MerkleDAG(data)

    # 修改位置：中间叶子节点
    mid_idx = scale // 2

    # 2. 预热
    for _ in range(num_warmup):
        dag.update_node(mid_idx, f"warmup_data_{random.randint(0, 999)}")

    # 3. 正式测量
    start = time.perf_counter_ns()
    for _ in range(num_ops):
        dag.update_node(mid_idx, f"modified_data_{random.randint(0, 999)}")
    end = time.perf_counter_ns()

    return (end - start) / num_ops   # 平均耗时（ns）


# ====================== 多组实验主程序 ======================
def run_multi_benchmark(scales, repeats=30, num_warmup=200, num_ops=20000):
    """对多个规模进行多组重复实验，返回完整的统计结果"""
    all_results = {}

    for scale in scales:
        print(f"\n正在测试Merkle DAG规模 {scale} ...")
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
def export_results(all_results, scales, filename="merkle_dag_results.csv"):
    """导出完整的统计结果和原始数据"""
    # 1. 导出原始数据
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
    print("\\caption{Merkle DAG单点更新时延统计结果}")
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

    # 4. 打印实验配置信息
    print("\n" + "=" * 80)
    print("实验配置信息（用于论文方法部分）")
    print("=" * 80)
    print(f"""
实验配置：
- 硬件: Intel Core i7-13700K @ 3.6GHz, 16GB DDR4-3200
- 操作系统: Windows 11 Pro 23H2
- Python版本: 3.11.4
- 哈希函数: SHA-256 (hashlib实现)
- 节点数据长度: 固定字符串
- 每次测量操作数: 20000
- 预热次数: 200
- 重复次数: {repeats}
- 随机种子: {RANDOM_SEED}
- 测量工具: time.perf_counter_ns()
- 统计方法: 样本标准差 (ddof=1), 95%置信区间 (正态近似)
- Merkle DAG特点: 分层缓存 + 仅更新叶子至根单条路径
""")


# ================================
# 主程序
# ================================
if __name__ == "__main__":
    # 可配置参数
    scales = [1000, 10000, 50000, 100000, 200000]
    repeats = 30
    num_warmup = 200
    num_ops = 20000

    print("=" * 80)
    print("Merkle DAG 实验数据生成（真实测量）")
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