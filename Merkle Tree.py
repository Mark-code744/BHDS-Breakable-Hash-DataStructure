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

# 纳秒高精度计时器
def precise_time():
    return time.perf_counter_ns()

# 全局统一SHA256哈希函数（和论文保持一致）
def sha256_hash(content):
    raw = str(content).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ====================== 标准Merkle树类 ======================
class RealMerkleTree:
    def __init__(self):
        self.leaves = []
        self.tree = []

    # 根据指定节点数量初始化整棵默克尔树
    def init_by_size(self, node_num):
        self.leaves = [sha256_hash(f"test_data_{i}") for i in range(node_num)]
        self.tree = self._build_tree()

    def _build_tree(self):
        tree_levels = [self.leaves.copy()]
        while len(tree_levels[-1]) > 1:
            curr = tree_levels[-1].copy()
            # 奇数叶子补最后一个配对
            if len(curr) % 2 != 0:
                curr.append(curr[-1])
            new_level = []
            for i in range(0, len(curr), 2):
                combine_str = curr[i] + curr[i+1]
                new_level.append(sha256_hash(combine_str))
            tree_levels.append(new_level)
        return tree_levels

    # 修改指定叶子节点，逐层向上更新路径 O(log n)
    def modify_leaf(self, idx, new_data):
        new_h = sha256_hash(new_data)
        self.leaves[idx] = new_h
        self.tree[0][idx] = new_h
        pos = idx
        level = 0
        # 循环向上更新父节点直至根
        while level + 1 < len(self.tree):
            parent_idx = pos // 2
            left = self.tree[level][2 * parent_idx]
            right = self.tree[level][2 * parent_idx + 1]
            self.tree[level+1][parent_idx] = sha256_hash(left + right)
            pos = parent_idx
            level += 1


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
    # 1. 构建Merkle树
    mt = RealMerkleTree()
    mt.init_by_size(scale)

    # 修改位置：中间叶子节点
    mid_pos = scale // 2

    # 2. 预热
    for _ in range(num_warmup):
        mt.modify_leaf(mid_pos, f"warmup_data_{random.randint(0, 999)}")

    # 3. 正式测量
    start = time.perf_counter_ns()
    for _ in range(num_ops):
        mt.modify_leaf(mid_pos, f"modified_data_{random.randint(0, 999)}")
    end = time.perf_counter_ns()

    return (end - start) / num_ops   # 平均耗时（ns）


# ====================== 多组实验主程序 ======================
def run_multi_benchmark(scales, repeats=30, num_warmup=200, num_ops=20000):
    """对多个规模进行多组重复实验，返回完整的统计结果"""
    all_results = {}

    for scale in scales:
        print(f"\n正在测试标准Merkle树规模 {scale} ...")
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
def export_results(all_results, scales, filename="merkle_tree_results.csv"):
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
    print("\\caption{标准Merkle树单点更新时延统计结果}")
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
- Merkle树分支因子: 2 (标准二叉树)
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
    print("标准Merkle树 实验数据生成（真实测量）")
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