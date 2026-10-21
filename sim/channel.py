# 第 1 步：信道模型
# 功能：
#   1. 生成 N 辆车在一条直路(路程)上的位置(离 RSU 基站的距离)
#   2. 根据"路径损耗"公式算出每辆车的信道增益
#   3. 由信道增益算出信噪比 SNR (衡量信号比噪声强多少)
#
# 通信常识(小白版)：
#   - 信号是无线传播的，传得越远就越弱，这叫"路径损耗"
#   - 信号越强、噪声越小，信息传得越快越可靠，我们用它来估计每辆车的速率

import numpy as np


def generate_vehicle_positions(n_vehicles, road_length=500.0, rng=None):
    """
    随机生成 n_vehicles 辆车在路上的位置。
    道路长度默认 500 米，RSU(基站)放在路中间(0 米处)。
    返回: 每辆车离 RSU 的距离(米)，一维数组，长度 n_vehicles
    """
    rng = rng or np.random.default_rng(42)  # 固定随机种子，保证每次结果可复现
    # 车随分布在 RSU 两侧：位置范围 [-road_length/2, +road_length/2]
    positions = rng.uniform(-road_length / 2, road_length / 2, size=n_vehicles)
    # 距离 = 离 0 点的绝对距离
    distances = np.abs(positions)
    return distances


def path_loss_db(distance_m, d0=1.0, path_loss_exponent=2.0):
    """
    路径损耗(以 dB 为单位)：
        损耗 = 10 * 路径损耗指数 * log10(距离 / 参考距离)
    距离越远，损耗越大(数字越大 = 信号损失越厉害)。
    path_loss_exponent: 开阔场景约 2，城市有遮挡时更大。
    """
    loss_db = 10.0 * path_loss_exponent * np.log10(np.maximum(distance_m, d0) / d0)
    return loss_db


def channel_gain(distance_m, transmit_power_db=30.0, path_loss_exponent=2.0):
    """
    计算每辆车的信道增益(能到达基站的信号强度比例，线性值)。
    信号 = 发射功率 - 路径损耗
    返回线性功率(非 dB)，方便后面做功率分配。
    """
    loss_db = path_loss_db(distance_m, path_loss_exponent=path_loss_exponent)
    received_power_db = transmit_power_db - loss_db
    gain = 10.0 ** (received_power_db / 10.0)  # 从 dB 转回线性值
    return gain


def compute_snr(gain, noise_power=1e-13):
    """
    由信道增益算信噪比 SNR = 信号功率 / 噪声功率。
    gain 是线性信号强度，noise_power 是热噪声功率(小常数)。
    返回线性 SNR(不是 dB)，方便后面映射成速率。
    """
    return gain / noise_power


def snr_to_rate(snr, bandwidth=1.0):
    """
    把 SNR 映射成每辆车能获得的速率(吞吐量)，单位 Mbps。
    用香农公式：速率 = 带宽 * log2(1 + SNR)
    这是通信里最基础的"信号越好，网速越快"公式。
    """
    rate = bandwidth * np.log2(1.0 + snr)  # 加 1 保证 SNR=0 时速率不为负
    return rate


if __name__ == "__main__":
    # ---- 自己运行一下(channel.py)时演示效果 ----
    n = 5
    dist = generate_vehicle_positions(n)
    gain = channel_gain(dist)
    snr = compute_snr(gain)
    rate = snr_to_rate(snr)

    print("车辆编号 | 距离(米) |   信道增益  |    SNR    |   速率(Mbps)")
    print("-" * 60)
    for i in range(n):
        print(f"   {i}    |  {dist[i]:.1f}   |  {gain[i]:.3e}  | {snr[i]:.1e} |  {rate[i]:.2f}")