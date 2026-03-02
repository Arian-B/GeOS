# ml_engine/rl_agent.py

import random
import pickle
import os

ACTIONS = ["ENERGY_SAVER", "BALANCED", "PERFORMANCE"]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QTABLE_FILE = os.path.join(BASE_DIR, "ml_engine", "q_table.pkl")

ALPHA = 0.1    # learning rate
GAMMA = 0.9    # discount factor
EPSILON = 0.1  # exploration rate

class RLAgent:
    def __init__(self):
        self.q = self.load()

    def discretize_state(self, data):
        cpu = "HIGH" if data["cpu_percent"] > 60 else "MED" if data["cpu_percent"] > 25 else "LOW"

        battery_val = data.get("battery")
        if battery_val is None:
            battery = "UNKNOWN"
        else:
            battery = "LOW" if battery_val < 30 else "MED" if battery_val < 70 else "HIGH"

        soil_val = data.get("soil_moisture")
        if soil_val is None:
            soil = "UNKNOWN"
        else:
            soil = "DRY" if soil_val < 30 else "OK"
        time = "DAY" if 6 <= data["hour"] <= 18 else "NIGHT"

        return (cpu, battery, soil, time)

    def choose_action(self, state):
        if random.random() < EPSILON:
            return random.choice(ACTIONS)
        return max(self.q.get(state, {}), key=self.q.get(state, {}).get, default="BALANCED")

    def update(self, state, action, reward, next_state):
        self.q.setdefault(state, {})
        self.q.setdefault(next_state, {})

        old = self.q[state].get(action, 0)
        future = max(self.q[next_state].values(), default=0)

        self.q[state][action] = old + ALPHA * (reward + GAMMA * future - old)

    def save(self):
        with open(QTABLE_FILE, "wb") as f:
            pickle.dump(self.q, f)

    def load(self):
        if os.path.exists(QTABLE_FILE):
            with open(QTABLE_FILE, "rb") as f:
                return pickle.load(f)
        return {}
