# 第 4 步: 完整仿真主程序
# 模拟"一条直路, 1 个 RSU + N 辆车移动", 跑 T 帧。
# 每帧: 车移动 -> 算新信道 -> 用各种调度算法分配 RB -> 记吞吐量/公平性
# 最后: 画各算法对比曲线 (吞吐量 / Jain 公平性 vs 时间)

import numpy as np
import matplotlib
matplotlib.use("Agg")  # 后台模式: 不弹窗, 直接保存图片(方便自动跑)
import matplotlib.pyplot as plt

# 让 matplotlib 显示中文
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

from . import channel as ch
from .schedulers import (schedulers_round_robin, schedulers_random,
                         schedulers_greedy, schedulers_pf)
from .metrics import compute_all


def run_simulation(n_vehicles=8, n_rb=24, n_frames=60,
                   schedulers=None, seed=42, speed=5.0):
    """
    主仿真。逐步看:
      1. 生成 N 辆车的位置和移动速度
      2. 一帧一帧推进时间, 每帧车往前开一点点, 信道随之变化
      3. 每帧用每个调度算法分 RB, 记录累计吞吐量 / 现在公平性
      4. 算出历史平均速率(供 PF 用)
    返回一个 dict: 每个算法名 -> {时间轴, 累计吞吐量, 公平性, 平均时延}
    """
    if schedulers is None:
        schedulers = ["round_robin", "random", "greedy", "pf"]

    rng = np.random.default_rng(seed)

    # 1) 生成车辆: 位置根据距离, 速度随机少量
    distances = ch.generate_vehicle_positions(n_vehicles, road_length=500.0, rng=rng)
    direction = rng.choice([-1, 1], size=n_vehicles)  # 向前/向后开
    vehicle_speed = rng.uniform(0.5, speed, size=n_vehicles) * direction

    # 历史平均速率(从 0 开始, 供 PF)
    past_avg_rate = np.ones(n_vehicles) * 1e-3

    # 结果容器
    results = {name: {"throughput": [], "jain": [], "delay": []}
               for name in schedulers}
    time_axis = list(range(n_frames))
    throughput_per_rb = 1.0

    # 2) 时间推进
    for frame in range(n_frames):
        # 车移动
        distances = distances + vehicle_speed
        distances = np.abs(distances) % 250.0 + 1.0  # 限制在 1~251 米, 不掉出范围

        # 当前信道
        gain = ch.channel_gain(distances)
        snr = ch.compute_snr(gain)
        rates_per_rb = ch.snr_to_rate(snr)  # 每辆车每个 RB 的实际速率

        # 3) 每个调度算法分配
        pf_rates = None
        for name in schedulers:
            if name == "round_robin":
                rates, _ = schedulers_round_robin(snr, throughput_per_rb, n_rb)
            elif name == "random":
                rates, _ = schedulers_random(snr, throughput_per_rb, n_rb, rng=rng)
            elif name == "greedy":
                rates, _ = schedulers_greedy(snr, throughput_per_rb, n_rb)
            elif name == "pf":
                rates, _ = schedulers_pf(snr, past_avg_rate, throughput_per_rb, n_rb)
                pf_rates = rates
            else:
                raise ValueError(f"未知算法: {name}")

            m = compute_all(rates)
            results[name]["throughput"].append(m["throughput"])
            results[name]["jain"].append(m["jain"])
            results[name]["delay"].append(m["delay"])

        # 4) 更新 PF 历史平均: 指数平滑(alpha越大多历史遗忘越快)。
        #    适当大的 alpha 保证"历史均值快速回归", 让被冷落的车能翻身, 避免锁死。
        alpha = 0.5
        if pf_rates is not None:
            # 所有车历史均值一起做指数平滑: 既计入本轮速率, 又让旧纪录缓慢衰退
            past_avg_rate = (1 - alpha) * past_avg_rate + alpha * pf_rates

    # 把 list 转成 numpy, 方便画图
    for name in schedulers:
        for k in results[name]:
            results[name][k] = np.array(results[name][k])
    return time_axis, results


def plot_results(time_axis, results, out_dir="results", prefix=""):
    """画 3 张对比图: 吞吐量 / 公平性 / 时延。"""
    import os
    os.makedirs(out_dir, exist_ok=True)

    # 图1: 每帧吞吐量
    plt.figure(figsize=(8, 5))
    for name, r in results.items():
        plt.plot(time_axis, r["throughput"], label=name, linewidth=2)
    plt.xlabel("时间 (仿真帧)")
    plt.ylabel("吞吐量 (Mbps)")
    plt.title("各调度算法每帧吞吐量对比")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    p1 = f"{out_dir}/{prefix}throughput.png"
    plt.savefig(p1, dpi=120)
    plt.close()

    # 图2: 公平性
    plt.figure(figsize=(8, 5))
    for name, r in results.items():
        plt.plot(time_axis, r["jain"], label=name, linewidth=2)
    plt.axhline(1.0, color="gray", linestyle="--", linewidth=1)
    plt.xlabel("时间 (仿真帧)")
    plt.ylabel("Jain 公平性")
    plt.title("各调度算法公平性对比 (1=绝对公平)")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    p2 = f"{out_dir}/{prefix}jain.png"
    plt.savefig(p2, dpi=120)
    plt.close()

    # 图3: 平均时延
    plt.figure(figsize=(8, 5))
    for name, r in results.items():
        plt.plot(time_axis, r["delay"], label=name, linewidth=2)
    plt.xlabel("时间 (仿真帧)")
    plt.ylabel("平均时延")
    plt.title("各调度算法平均时延对比")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    p3 = f"{out_dir}/{prefix}delay.png"
    plt.savefig(p3, dpi=120)
    plt.close()

    print(f"已保存: {p1}")
    print(f"已保存: {p2}")
    print(f"已保存: {p3}")


if __name__ == "__main__":
    # 第 6 步: 完整对比 4 种算法 (轮询 + 随机 + 贪心 + 比例公平)
    time_axis, results = run_simulation(
        n_vehicles=8, n_rb=24, n_frames=60,
        schedulers=["round_robin", "random", "greedy", "pf"],
    )
    plot_results(time_axis, results, prefix="step6_")
    print("第 6 步完成:", {k: f"吞吐≈{v['throughput'].mean():.1f} 公平={v['jain'].mean():.3f}"
                         for k, v in results.items()})