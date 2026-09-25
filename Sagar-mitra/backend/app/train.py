import os
import sys
import numpy as np

# Add backend directory to path so it can import app.marine_env
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_dir)

from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from app.marine_env import ArabianSeaRouteEnv, plot_environment, plan_route

def main():
    print("Initializing Generalized Goal-Conditioned Arabian Sea Environment...")
    env = ArabianSeaRouteEnv(randomize_on_reset=True)

    # Validate environment compliance
    check_env(env, warn=True)
    print("Environment check passed successfully!")

    # Initialize the PPO agent with goal-conditioned MLP policy
    tensorboard_log_dir = os.path.join(backend_dir, "ppo_marine_tensorboard")
    model = PPO("MlpPolicy", env, verbose=1, tensorboard_log=tensorboard_log_dir)

    print("Starting Goal-Conditioned PPO Training across diverse Point A -> Point B routes (40,000 steps)...")
    model.learn(total_timesteps=40000)

    # Save trained weights
    models_dir = os.path.join(backend_dir, "models")
    os.makedirs(models_dir, exist_ok=True)
    model_save_path = os.path.join(models_dir, "ppo_marine_navigator")
    model.save(model_save_path)
    print(f"Trained generalized model saved to {model_save_path}.zip")

    # --- TEST 1: Route from Mumbai (18.922, 72.833) to Offshore Target (15.5, 71.2) ---
    print("Testing generalized route planner from Mumbai (18.922, 72.833) to Offshore Target (15.5, 71.2)...")
    plot_path1 = os.path.join(backend_dir, "static", "plots", "rl_route_trajectory.png")
    traj1, summary1 = plan_route(
        start_pos=(18.922, 72.833),
        target_pos=(15.5, 71.2),
        model_path=model_save_path + ".zip",
        save_path=plot_path1
    )
    print("Route 1 Summary:", summary1)

    # --- TEST 2: Route from Ratnagiri (16.99, 73.28) to Southern Target (13.5, 72.0) ---
    print("Testing generalized route planner from Ratnagiri (16.99, 73.28) to Southern Target (13.5, 72.0)...")
    plot_path2 = os.path.join(backend_dir, "static", "plots", "custom_route_A_to_B.png")
    traj2, summary2 = plan_route(
        start_pos=(16.99, 73.28),
        target_pos=(13.5, 72.0),
        model_path=model_save_path + ".zip",
        save_path=plot_path2
    )
    print("Route 2 Summary:", summary2)

if __name__ == "__main__":
    main()