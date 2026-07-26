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

# 高精度纳秒计时器（全局统一）
def precise_time():
    return time.perf_counter_ns()

# 全局统一SHA256哈希函数，所有实验共用
def sha256_hash(content):
    raw = str(content).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ====================== 动态Merkle树类 ======================
class DynamicMerkleTree:
    def __init__(self, data):
        self.origin_data = data.copy()
        self.layers = []  # 缓存整棵树所有层级哈希，实现增量更新
        self.root = None
        self.build_full_tree()

    def build_full_tree(self):
        # 初始化并缓存全部层级
        current = [sha256_hash(d) for d in self.origin_data]
        self.layers = [current.copy()]
        while len(current) > 1:
            if len(current) % 2 != 0:
                current.append(current[-1])
            new_level = []
            for i in range(0, len(current), 2):
                combine = current[i] + current[i+1]
                new_level.append(sha256_hash(combine))
            self.layers.append(new_level)
            current = new_level
        self.root = self.layers[-1][0]

    def update_node(self, idx, new_val):
        # 仅向上更新单条叶子至根路径，不重建整树，真实O(log n)
        self.origin_data[idx] = new_val
        # 修改叶子层对应位置
        self.layers[0][idx] = sha256_hash(new_val)
        curr_pos = idx
        # 逐层向上刷新受影响父节点
        for depth in range(1, len(self.layers)):
            parent_idx = curr_pos // 2
            left = self.layers[depth-1][2 * parent_idx]
            right = self.layers[depth-1][2 * parent_idx + 1]
            self.layers[depth][parent_idx] = sha256_hash(left + right)
            curr_pos = parent_idx
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
    # 1. 构建动态Merkle树
    data = [f"Block_{i}" for i in range(scale)]
    dmt = DynamicMerkleTree(data)

    # 修改位置：中间叶子节点
    mid_idx = scale // 2

    # 2. 预热
    for _ in range(num_warmup):
        dmt.update_node(mid_idx, f"warmup_data_{random.randint(0, 999)}")

    # 3. 正式测量
    start = time.perf_counter_ns()
    for _ in range(num_ops):
        dmt.update_node(mid_idx, f"modified_data_{random.randint(0, 999)}")
    end = time.perf_counter_ns()

    return (end - start) / num_ops   # 平均耗时（ns）


# ====================== 多组实验主程序 ======================
def run_multi_benchmark(scales, repeats=30, num_warmup=200, num_ops=20000):
    """对多个规模进行多组重复实验，返回完整的统计结果"""
    all_results = {}

    for scale in scales:
        print(f"\n正在测试动态Merkle树规模 {scale} ...")
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
def export_results(all_results, scales, filename="dynamic_merkle_results.csv"):
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
    print("\\caption{动态Merkle树单点更新时延统计结果}")
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
- 动态Merkle树特点: 缓存全树层级，更新仅迭代单条叶子至根路径
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
    print("动态Merkle树 实验数据生成（真实测量）")
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