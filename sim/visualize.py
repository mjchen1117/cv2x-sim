# 第 7 步: 柱状图 + GIF 动画可视化
# 1) 柱状图: 对比各算法的平均 吞吐量 / 公平性 / 时延
# 2) GIF   : 动画显示车辆移动时, 各调度算法的资源分配过程

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

from .run import run_simulation
from . import channel as ch
from .schedulers import (schedulers_round_robin, schedulers_random,
                         schedulers_greedy, schedulers_pf)

ALGO_LABELS = {
    "round_robin": "轮询",
    "random": "随机",
    "greedy": "贪心",
    "pf": "比例公平",
}
ALGO_COLORS = {
    "round_robin": "#1f77b4",
    "random": "#ff7f0e",
    "greedy": "#2ca02c",
    "pf": "#d62728",
}


def plot_bar_charts(results, out_dir="results"):
    """柱状图: 平均吞吐 / 平均公平性 / 平均时延。"""
    names = list(results.keys())
    avg_throughput = [results[n]["throughput"].mean() for n in names]
    avg_jain = [results[n]["jain"].mean() for n in names]
    avg_delay = [results[n]["delay"].mean() for n in names]
    labels = [ALGO_LABELS[n] for n in names]

    # 三张柱状图
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    datasets = [("平均吞吐量 (Mbps)", avg_throughput, "吞吐量"),
                ("平均公平性 (Jain指数)", avg_jain, "公平性"),
                ("平均时延", np.clip(avg_delay, 0, 100), "时延")]
    for ax, (title, data, kind) in zip(axes, datasets):
        colors = [ALGO_COLORS[n] for n in names]
        ax.bar(labels, data, color=colors)
        ax.set_title(title)
        ax.set_ylabel(title)
        ax.grid(axis="y", alpha=0.3)
        for i, v in enumerate(data):
            ax.text(i, v, f"{v:.2f}", ha="center", va="bottom", fontsize=9)
    fig.suptitle("四种调度算法平均性能对比", fontsize=14)
    fig.tight_layout()
    p = f"{out_dir}/step7_bar_charts.png"
    fig.savefig(p, dpi=120)
    plt.close(fig)
    print(f"柱状图已保存: {p}")


def make_gif(n_vehicles=8, n_rb=24, n_frames=40, out_dir="results"):
    """GIF 动画: 车辆移动 + 各算法资源块分配给谁。

    画面说明: 底部一条道路, RSU 在中间(0 米), 车用小圆圈表示。
    上方用四根横排的小条表示各算法当前把 RB 分给了哪辆车(颜色对应车)。
    """
    import os
    rng = np.random.default_rng(123)
    distances = ch.generate_vehicle_positions(n_vehicles, road_length=500.0, rng=rng)
    speed = rng.choice([-1, 1], n_vehicles) * rng.uniform(0.5, 5, n_vehicles)
    past_avg = np.ones(n_vehicles) * 1e-3
    algs = ["round_robin", "random", "greedy", "pf"]

    fig, ax = plt.subplots(figsize=(10, 6))

    # 车道(底部) + 4 个算法行的分隔位置
    road_level = -1
    alg_rows = {"round_robin": 0, "random": 1, "greedy": 2, "pf": 3}

    def draw_frame(frame_idx):
        ax.clear()
        nonlocal distances, past_avg
        # 车辆移动
        distances = (np.abs(distances + speed) % 250.0) + 1.0
        gain = ch.channel_gain(distances)
        snr = ch.compute_snr(gain)

        # 画道路和 RSU
        xs = np.linspace(35, 465, 300)          # 可视化用像素坐标映射
        ax.plot(xs, [road_level]*300, color="gray", linewidth=4)
        ax.scatter([250], [road_level], c="red", s=120, marker="^", label="RSU")
        # 画车辆位置 (映射到横轴)
        car_x = 250 + (distances - 1) * (215 / 124)  # 简单线性映射
        ax.scatter(car_x, [road_level]*n_vehicles, c=plt.cm.tab10(np.arange(n_vehicles)),
                   s=80, zorder=5)

        # 对每个算法, 画一横行 RB 分配(小方块)
        for idx, name in enumerate(algs):
            yrow = alg_rows[name]
            ax.text(10, yrow, ALGO_LABELS[name], fontsize=10, va="center")
            if name == "round_robin":
                rates, counts = schedulers_round_robin(snr, 1.0, n_rb)
            elif name == "random":
                rates, counts = schedulers_random(snr, 1.0, n_rb, rng=rng)
            elif name == "greedy":
                rates, counts = schedulers_greedy(snr, 1.0, n_rb)
            else:
                rates, counts = schedulers_pf(snr, past_avg, 1.0, n_rb)

            # 画每个 RB 的归属(颜色=车辆)
            owners = _rb_owners_by_alg(name, snr, past_avg, n_rb, rng)
            for rb, owner in enumerate(owners):
                xb = 60 + rb * (380 / n_rb)
                ax.barh(yrow, width=(380 / n_rb) - 2, left=xb, height=0.6,
                        color=plt.cm.tab10(owner), alpha=0.85)

            ax.set_ylim(-1.6, 4.2)

        ax.set_xlim(0, 480)
        ax.set_title(f"帧 {frame_idx+1}/{n_frames} · 各算法资源块(RB)分配车辆")
        ax.set_yticks([])
        ax.set_xticks([])
        ax.legend(loc="upper right")

        # 记录 PF 历史均值更新
        if "pf" in algs:
            rates_pf, _ = schedulers_pf(snr, past_avg, 1.0, n_rb)
            past_avg = 0.5 * past_avg + 0.5 * rates_pf

    anim = FuncAnimation(fig, draw_frame, frames=n_frames, interval=200)
    gif_path = f"{out_dir}/step7_scheduling.gif"
    anim.save(gif_path, writer="pillow", dpi=80)
    plt.close(fig)
    print(f"GIF 已保存: {gif_path}")


def _rb_owners_by_alg(name, snr, past_avg, n_rb, rng):
    """返回该算法本帧每个 RB 的车主编号(用于动画上色)。"""
    from .schedulers import snr_to_rate  # noqa: F401
    import numpy as np
    owners = []
    if name == "round_robin":
        for rb in range(n_rb):
            owners.append(rb % len(snr))
    elif name == "random":
        for rb in range(n_rb):
            owners.append(int(rng.integers(0, len(snr))))
    elif name == "greedy":
        best = int(np.argmax(snr))
        owners = [best]*n_rb
    elif name == "pf":
        w = snr_to_rate(snr) / np.maximum(past_avg, 1e-9)
        p = w / w.sum()
        for rb in range(n_rb):
            owners.append(int(np.random.choice(len(snr), p=p)))
    return owners


if __name__ == "__main__":
    import os
    os.makedirs("results", exist_ok=True)
    # 跑一次仿真拿平均指标
    _, results = run_simulation(
        n_vehicles=8, n_rb=24, n_frames=60,
        schedulers=["round_robin", "random", "greedy", "pf"],
    )
    plot_bar_charts(results)
    make_gif(n_vehicles=8, n_rb=24, n_frames=40)