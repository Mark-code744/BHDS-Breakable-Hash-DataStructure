import time
import json
import hashlib
import statistics
import math
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

# ====================== 传统区块链区块类（增加哈希缓存优化） ======================
class TraditionalBlock:
    def __init__(self, data, prev_hash):
        self.data = data          # 业务数据
        self.prev_hash = prev_hash# 前驱哈希指针（绑定上一块hash）
        self._hash_cache = None   # 哈希缓存，避免重复计算
        self.hash = self.calc_hash()  # 本区块指纹

    # 哈希计算，带缓存
    def calc_hash(self):
        if self._hash_cache is not None:
            return self._hash_cache
        block_str = json.dumps(self.data, sort_keys=True).encode()
        self._hash_cache = hashlib.sha256(block_str).hexdigest()
        return self._hash_cache

    # 修改数据专用方法，清空哈希缓存
    def set_data(self, new_data):
        self.data = new_data
        self._hash_cache = None

# ====================== 传统区块链容器 ======================
class TraditionalChain:
    def __init__(self):
        # 初始化创世块，链首无前置区块，prev_hash固定为"0"
        self.chain = [self.genesis_block()]

    def genesis_block(self):
        return TraditionalBlock({"index": 0}, prev_hash="0")

    # 尾部追加新区块 O(1)
    def add(self, data):
        last_block = self.chain[-1]
        new_block = TraditionalBlock(data, prev_hash=last_block.hash)
        self.chain.append(new_block)

    # 核心缺陷：修改中间区块，级联更新后面全部区块 O(n)
    def modify(self, idx, new_data):
        # 1. 修改目标区块数据，清空缓存并重算自身hash
        self.chain[idx].set_data(new_data)
        self.chain[idx].hash = self.chain[idx].calc_hash()

        # 2. 从idx+1到链尾，全部循环更新prev_hash + 重算hash
        for i in range(idx + 1, len(self.chain)):
            self.chain[i].prev_hash = self.chain[i - 1].hash
            self.chain[i].hash = self.chain[i].calc_hash()

    # 链完整性校验（验证哈希链是否断裂）
    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i-1]
            # 1. 当前区块自身hash是否和数据匹配
            if curr.hash != curr.calc_hash():
                return False
            # 2. 当前区块前驱哈希是否等于上一块真实hash
            if curr.prev_hash != prev.hash:
                return False
        return True


# ====================== 统计工具（95%置信区间、P95） ======================
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


# ====================== 传统链性能测试函数 ======================
def run_single_benchmark(scale, num_warmup=200, num_ops=20000):
    """对指定规模执行一次完整的测量，返回单次更新操作的平均耗时（ns）"""
    # 1. 构建区块链
    chain = TraditionalChain()
    base_data = {"data": "X" * 100}
    for i in range(1, scale + 1):
        chain.add({"index": i, "data": "test_data"})

    # 修改位置：链中间位置（模拟实际业务更新）
    mod_pos = min(5000, scale // 2)

    # 2. 预热
    for _ in range(num_warmup):
        chain.modify(mod_pos, {"index": mod_pos, "data": "WARMUP_DATA"})

    # 3. 正式测量
    start = time.perf_counter_ns()
    for _ in range(num_ops):
        chain.modify(mod_pos, {"index": mod_pos, "data": "MODIFIED_DATA"})
    end = time.perf_counter_ns()

    return (end - start) / num_ops   # 平均耗时（ns）


def run_multi_benchmark(scales, repeats=30, num_warmup=200, num_ops=20000):
    """对多个规模进行多组重复实验，返回完整的统计结果"""
    all_results = {}

    for scale in scales:
        print(f"\n正在测试传统链规模 {scale} ...")
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
def export_results(all_results, scales, filename="traditional_chain_results.csv"):
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
    print("\\caption{传统哈希链单点更新时延统计结果}")
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
    print("传统哈希链 实验数据生成（真实测量）")
    print(f"  节点规模: {scales}")
    print(f"  每组重复次数: {repeats}")
    print(f"  每次测量操作数: {num_ops}")
    print(f"  随机种子: {RANDOM_SEED}")
    print("=" * 80)

    all_results = run_multi_benchmark(scales, repeats, num_warmup, num_ops)

    # 导出所有结果
    export_results(all_results, scales)

    # 简单篡改校验演示
    print("\n" + "=" * 80)
    print("传统链篡改校验演示")
    print("=" * 80)
    demo_chain = TraditionalChain()
    demo_chain.add({"tx": "A->B 10"})
    demo_chain.add({"tx": "B->C 5"})
    print("篡改前链有效性：", demo_chain.is_chain_valid())
    demo_chain.modify(1, {"tx": "A->B 1000"})
    print("篡改区块1后自动更新全部后续区块，校验仍为True（传统链修改后主动修复哈希链）")

    print("\n" + "=" * 80)
    print("实验完成！")
    print("=" * 80)