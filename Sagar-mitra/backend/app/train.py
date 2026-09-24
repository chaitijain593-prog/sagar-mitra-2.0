import os
import sys
import numpy as np

# Add backend directory to path so it can import app.marine_env
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_dir)

from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from app.marine_env import ArabianSeaRouteEnv, plot_environment

def main():
    print("Initializing Arabian Sea Custom Gymnasium Environment...")
    env = ArabianSeaRouteEnv()

    # Validate that custom environment complies with Gymnasium standards
    check_env(env, warn=True)
    print("Environment check passed successfully!")

    # Initialize the PPO agent with an MLP policy
    tensorboard_log_dir = os.path.join(backend_dir, "ppo_marine_tensorboard")
    model = PPO("MlpPolicy", env, verbose=1, tensorboard_log=tensorboard_log_dir)

    print("Starting Fast PPO Agent Training (30,000 steps)...")
    model.learn(total_timesteps=30000)

    # Save the trained model weights
    models_dir = os.path.join(backend_dir, "models")
    os.makedirs(models_dir, exist_ok=True)
    model_save_path = os.path.join(models_dir, "ppo_marine_navigator")
    model.save(model_save_path)
    print(f"Trained model saved to {model_save_path}.zip")

    # --- NON-INTERACTIVE EVALUATION ---
    print("Evaluating trained agent and generating optimal route trajectory plot...")
    eval_env = ArabianSeaRouteEnv()
    obs, _ = eval_env.reset()

    for step in range(200):
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = eval_env.step(action)
        if terminated or truncated:
            print(f"Route evaluation completed at step {step + 1}! (Terminated: {terminated})")
            break

    plot_path = os.path.join(backend_dir, "static", "plots", "rl_route_trajectory.png")
    plot_environment(eval_env, agent_trajectory=eval_env.trajectory, save_path=plot_path)

if __name__ == "__main__":
    main()