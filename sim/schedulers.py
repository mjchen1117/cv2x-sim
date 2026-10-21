# 第 2 步：资源分配(调度)算法
# 每种算法接收: 每辆车当前的信噪比 snr, 以及历史平均速率 past_avg_rate(供 PF 用)
# 返回: 一个数组 allocation, 表示把 T 个资源块分给 N 辆车后, 每辆车的累计速率

import numpy as np
from .channel import snr_to_rate


def schedulers_round_robin(snr, throughput_per_rb, n_rb):
    """
    轮询: 资源块按顺序轮流分给每辆车 (0,1,2,...,N-1,0,1,2,...)
    优点: 绝对公平; 缺点: 不考虑信号好坏, 把高速RB浪费给慢车
    说明: 每个 RB 被某辆车道占用时, 速度用那辆车自己的信道速率。
    """
    rates_per_rb = snr_to_rate(snr)       # 每辆车一个RB能带来的速率
    n_vehicles = len(snr)
    # 累加: 每个 RB 分给 owner 车, 就累加那辆车的速率
    rates = np.zeros(n_vehicles)
    allocation_counts = np.zeros(n_vehicles)
    for rb in range(n_rb):
        owner = rb % n_vehicles           # 轮流指认车主
        allocation_counts[owner] += 1
        rates[owner] += rates_per_rb[owner]
    return rates, allocation_counts


def schedulers_random(snr, throughput_per_rb, n_rb, rng=None):
    """
    随机: 每个资源块随机扔给任意一辆车
    缺点: 完全看运气, 有人饱有人饿, 且依赖于随机种子。
    """
    rates_per_rb = snr_to_rate(snr)
    rng = rng or np.random.default_rng(1)
    n_vehicles = len(snr)
    rates = np.zeros(n_vehicles)
    allocation_counts = np.zeros(n_vehicles)
    for rb in range(n_rb):
        owner = rng.integers(0, n_vehicles)   # 随机选一辆车
        allocation_counts[owner] += 1
        rates[owner] += rates_per_rb[owner]

    return rates, allocation_counts


def schedulers_greedy(snr, throughput_per_rb, n_rb):
    """
    贪心: 每个资源块都给信号最好(速率最高)的那辆车
    优点: 总速率(吞吐量)最大化; 缺点: 信号差的车永远挨饿, 极不公平
    """
    rates_per_rb = snr_to_rate(snr)          # 每辆车每个 RB 的实际速率
    n_vehicles = len(snr)
    allocation_counts = np.zeros(n_vehicles)

    # 每次把 RB 给当前速率最快的车
    best_vehicle = int(np.argmax(rates_per_rb))
    allocation_counts[best_vehicle] = n_rb

    rates = rates_per_rb * allocation_counts
    return rates, allocation_counts


def schedulers_pf(snr, past_avg_rate, throughput_per_rb, n_rb):
    """
    比例公平(Proportional Fair, PF):
    核心思想: 每个 RB 分配给 [当前速率 / 历史平均速率] 比值最大的车
    关键是"每分配一个RB后马上更新该车的历史均值":
        - 被选中 的车 历史均值上升 → 比值下降 → 下次不易再被选(给他让步)
        - 没被选中 的车 历史均值不动 → 相对比值上升 → 慢慢能被分到
    这样: 信号好的车高效利用, 但信号差的车也不会被永久饿死 → 又快又相对公平。
    past_avg_rate: 每辆车的历史平均速率(会被原地更新), 分配时用; 返回更新后的值。
    """
    owner_seq = _pf_owners(snr, past_avg_rate, n_rb)
    rates_per_rb = snr_to_rate(snr)
    n_vehicles = len(snr)
    rates = np.zeros(n_vehicles)
    allocation_counts = np.zeros(n_vehicles)
    for owner in owner_seq:
        allocation_counts[owner] += 1
        rates[owner] += rates_per_rb[owner]
    return rates, allocation_counts


def _pf_owners(snr, past_avg_rate, n_rb):
    """返回 PF 逐 RB 分配给的车主序列。
    标准 PF: 用本帧固定的历史均值 R_k 算权重 w_k = rate_k / R_k,
    再把 RB 按权重 比例/随机 分给多辆车, 避免"winner-takes-all 锁死"。
    """
    rates_per_rb = snr_to_rate(snr)
    avg = np.maximum(np.asarray(past_avg_rate, dtype=float), 1e-9)
    weight = rates_per_rb / avg          # 每辆车的 PF 权重(固定用于本帧)

    owners = []
    for rb in range(n_rb):
        # 按权重的概率抽样(而不是单取自最大), 让每辆车都有机会
        p = weight / weight.sum()
        best = int(np.random.choice(len(weight), p=p))
        owners.append(best)
    return owners


# 调度器注册表: 名字 -> 函数
SCHEDULERS = {
    "round_robin": schedulers_round_robin,   # 轮询
    "random":      schedulers_random,        # 随机
    "greedy":      schedulers_greedy,        # 贪心(稍后开启)
    "pf":          schedulers_pf,            # 比例公平(稍后开启)
}


if __name__ == "__main__":
    # ---- 演示: 用一组合适的 SNR 看两种算法的差别 ----
    np.random.seed(42)
    n_vehicles = 5
    n_rb = 10

    # 构造一组 SNR, 让不同车的信道好坏不同(用一个距离近似的假信道)
    from .channel import snr_to_rate, compute_snr, channel_gain, generate_vehicle_positions
    dist = generate_vehicle_positions(n_vehicles)
    gain = channel_gain(dist)
    snr = compute_snr(gain)
    tpr = 1.0  # 假设每个 RB 给 1 (简化演示)

    print(f"共 {n_vehicles} 辆车, {n_rb} 个资源块\n")
    for name, func in [("round_robin", schedulers_round_robin),
                       ("random", schedulers_random),
                       ("greedy", schedulers_greedy)]:
        if name == "random":
            rates, counts = func(snr, tpr, n_rb)
        else:
            rates, counts = func(snr, tpr, n_rb)
        print(f"[{name}] 每车RB数: {counts.astype(int)}, 每车速率: {rates.round(2)}")
        print(f"        总吞吐量: {rates.sum():.2f}\n")