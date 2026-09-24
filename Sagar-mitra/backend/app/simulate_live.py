import os
import sys
import time
import numpy as np
import matplotlib.pyplot as plt

# Add backend directory to path so it can import app.marine_env
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_dir)

from stable_baselines3 import PPO
from app.marine_env import ArabianSeaRouteEnv

def main():
    print("🌊 Starting Live Maritime Agent Navigation Simulation...")
    model_path = os.path.join(backend_dir, "models", "ppo_marine_navigator.zip")
    
    if os.path.exists(model_path):
        print(f"📦 Loading trained PPO model from {model_path}...")
        model = PPO.load(model_path)
    else:
        print("⚠️ No trained model weights found, using random action policy...")
        model = None

    env = ArabianSeaRouteEnv(render_mode="human")
    obs, _ = env.reset()

    print("🚀 Running live navigation episode...")
    for step in range(200):
        if model is not None:
            action, _states = model.predict(obs, deterministic=True)
        else:
            action = env.action_space.sample()

        obs, reward, terminated, truncated, info = env.step(action)
        time.sleep(0.05) # Small delay for smooth visual playback

        if terminated or truncated:
            print(f"🏁 Navigation episode completed at step {step + 1}! (Terminated: {terminated}, Truncated: {truncated})")
            break

    print("📊 Simulation complete. Keep plot window open to inspect final route.")
    plt.ioff()
    plt.show(block=True)

if __name__ == "__main__":
    main()
