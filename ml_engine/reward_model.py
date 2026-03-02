# ml_engine/reward_model.py

def compute_reward(state, action):
    cpu, battery, soil, time = state

    reward = 0

    if soil == "DRY" and action == "PERFORMANCE":
        reward += 2

    if battery == "LOW" and action == "ENERGY_SAVER":
        reward += 2

    if battery == "HIGH" and action == "ENERGY_SAVER":
        reward -= 1

    if soil == "DRY" and action != "PERFORMANCE":
        reward -= 2

    if cpu == "HIGH" and action == "PERFORMANCE":
        reward += 1

    return reward


def compute_reward_continuous(features, action):
    """
    Reward model for true optimization using raw telemetry features.
    Higher reward = better decision for energy efficiency + farm health.
    """
    cpu = features.get("cpu_percent")
    load = features.get("load_avg")
    mem = features.get("memory_percent")
    battery = features.get("battery")
    soil = features.get("soil_moisture")
    temp = features.get("temperature")

    reward = 0.0

    # Base preference: balanced is neutral, saver conserves, performance costs more.
    if action == "ENERGY_SAVER":
        reward += 0.4
    elif action == "PERFORMANCE":
        reward -= 0.4

    # Battery-aware optimization
    if battery is not None:
        if battery < 20:
            reward += 2.5 if action == "ENERGY_SAVER" else -1.5
        elif battery > 80 and action == "ENERGY_SAVER":
            reward -= 0.5

    # Soil moisture optimization
    if soil is not None:
        if soil < 30:
            reward += 2.0 if action == "PERFORMANCE" else -0.8
        elif soil > 60 and action == "ENERGY_SAVER":
            reward += 0.6

    # Temperature safety
    if temp is not None and temp > 35:
        reward += 0.8 if action == "ENERGY_SAVER" else -0.5

    # System load protection
    if cpu is not None:
        if cpu > 80:
            reward += 1.0 if action == "ENERGY_SAVER" else -0.7
        elif cpu < 40 and action == "PERFORMANCE":
            reward += 0.3

    if mem is not None and mem > 80:
        reward += 0.7 if action == "ENERGY_SAVER" else -0.5

    if load is not None and load > 2.0:
        reward += 0.6 if action == "ENERGY_SAVER" else -0.4

    return reward
