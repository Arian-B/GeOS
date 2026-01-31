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
