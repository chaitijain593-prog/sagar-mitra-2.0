import os
import sys
import time
import argparse
import numpy as np
import matplotlib.pyplot as plt

# Add backend directory to path so it can import app.marine_env
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_dir)

from stable_baselines3 import PPO
from app.marine_env import ArabianSeaRouteEnv

def main():
    parser = argparse.ArgumentParser(description="Live Simulation for Arbitrary Point A to Point B Navigation")
    parser.add_argument("--start_lat", type=float, default=18.922, help="Start Latitude (Point A)")
    parser.add_argument("--start_lon", type=float, default=72.833, help="Start Longitude (Point A)")
    parser.add_argument("--target_lat", type=float, default=15.5, help="Target Latitude (Point B)")
    parser.add_argument("--target_lon", type=float, default=71.2, help="Target Longitude (Point B)")
    args = parser.parse_args()

    start_pos = (args.start_lat, args.start_lon)
    target_pos = (args.target_lat, args.target_lon)

    print(f"🌊 Starting Live Navigation Simulation: Point A {start_pos} -> Point B {target_pos}...")
    model_path = os.path.join(backend_dir, "models", "ppo_marine_navigator.zip")
    
    if os.path.exists(model_path):
        print(f"📦 Loading trained generalized PPO model from {model_path}...")
        model = PPO.load(model_path)
    else:
        print("⚠️ No trained model weights found, using goal-directed navigation policy...")
        model = None

    env = ArabianSeaRouteEnv(render_mode="human")
    obs, info = env.reset(options={"start_pos": start_pos, "target_pos": target_pos})

    print("🚀 Running live navigation episode...")
    for step in range(env.max_steps):
        if model is not None:
            action, _states = model.predict(obs, deterministic=True)
        else:
            vec = np.array(target_pos) - env.current_pos
            norm = np.linalg.norm(vec)
            action = (vec / norm) * 0.08 if norm > 1e-6 else np.zeros(2, dtype=np.float32)

        obs, reward, terminated, truncated, info = env.step(action)
        time.sleep(0.04)

        if terminated or truncated:
            print(f"🏁 Navigation episode completed at step {step + 1}! (Terminated: {terminated}, Truncated: {truncated})")
            break

    print("📊 Simulation complete. Keep plot window open to inspect final route.")
    plt.ioff()
    plt.show(block=True)

if __name__ == "__main__":
    main()
