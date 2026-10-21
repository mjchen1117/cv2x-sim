# 第 3 步: 性能指标计算
# 三个核心指标: 吞吐量 / 公平性(Jain指数) / 时延

import numpy as np


def throughput(rates):
    """总吞吐量: 所有车速率之和。单位与 rates 一致(Mbps)。"""
    return float(np.sum(rates))


def jain_index(rates):
    """
    公平性(Jain 指数), 取值 0~1:
      1 = 绝对公平(人人都一样), 越接近 1 越公平。
    公式: (sum(rates))^2 / (n * sum(rates^2))
    注意: 当有人速率是 0 时, 公平性会显著下降(因为饿死的车拉低平均值)。
    """
    rates = np.asarray(rates, dtype=float)
    n = float(len(rates))
    if n == 0:
        return 0.0
    sum_r = np.sum(rates)
    if sum_r == 0:
        return 0.0
    return float(sum_r ** 2 / (n * np.sum(rates ** 2)))


def average_delay(rates):
    """
    平均时延: 近似用 1 / 速率 的均值来估计。
    直觉: 速率越高, 等得越短; 速率越低(饿死/很少), 等得越久。
    速率接近 0 的车时延会很大, 体现"被饿死"的代价。
    """
    rates = np.asarray(rates, dtype=float)
    # 速率太小就当作很小(避免除以 0), 时延上限给一个合理值
    delay_per_vehicle = 1.0 / np.maximum(rates, 1e-3)
    return float(np.mean(delay_per_vehicle))


def compute_all(rates):
    """一次性算三个指标, 返回字典。"""
    return {
        "throughput": throughput(rates),
        "jain": jain_index(rates),
        "delay": average_delay(rates),
    }


if __name__ == "__main__":
    # 演示: 三种算法各跑一遍, 看指标差异
    import numpy as np
    from .channel import compute_snr, channel_gain, generate_vehicle_positions
    from .schedulers import (schedulers_round_robin, schedulers_random,
                             schedulers_greedy)

    np.random.seed(42)
    n = 8
    n_rb = 24
    dist = generate_vehicle_positions(n)
    snr = compute_snr(channel_gain(dist))
    tpr = 1.0

    print(f"{'算法':<14}{'吞吐量':>10}{'Jain公平性':>12}{'平均时延':>12}")
    print("-" * 50)

    cases = {
        "轮詢": schedulers_round_robin,
        "随机": schedulers_random,
        "贪心": schedulers_greedy,
    }
    for name, func in cases.items():
        if name == "随机":
            rates, _ = func(snr, tpr, n_rb)
        else:
            rates, _ = func(snr, tpr, n_rb)
        m = compute_all(rates)
        print(f"{name:<14}{m['throughput']:>10.2f}  {m['jain']:>10.4f}  {m['delay']:>10.2f}")