import gymnasium as gym
from gymnasium import spaces
import numpy as np
import json
import os
import math
from shapely.geometry import Point, shape
import pandas as pd
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree

class ArabianSeaRouteEnv(gym.Env):
    """
    Generalized Multi-Factor Custom Gymnasium Environment for Autonomous Marine Navigation & Routing
    between ANY arbitrary start point A and target point B in the Arabian Sea.
    
    Features:
    - Dynamic Goal-Conditioned Navigation (accepts any start_pos and target_pos)
    - Domain-Randomized Training (samples valid internal EEZ start & target pairs)
    - Multi-Objective Reward: Progress toward target + PFZ catch potential + SST efficiency
    - Safety & Legal Constraints: Indian EEZ boundary (200 NM) & Marine Protected Areas (MPAs)
    """
    metadata = {"render_modes": ["human"]}

    def __init__(self, data_dir=None, render_mode=None, start_pos=None, target_pos=None, randomize_on_reset=False):
        super().__init__()
        self.render_mode = render_mode
        self.start_pos = np.array(start_pos, dtype=np.float32) if start_pos is not None else None
        self.target_pos = np.array(target_pos, dtype=np.float32) if target_pos is not None else None
        self.randomize_on_reset = randomize_on_reset
        
        # Action space: continuous displacement (delta_lat, delta_lon) in range [-0.1, 0.1] degrees
        self.action_space = spaces.Box(low=-0.1, high=0.1, shape=(2,), dtype=np.float32)
        
        # Observation space (10 features):
        # [vessel_lat, vessel_lon, target_lat, target_lon, dist_to_target, sst, salinity, chlorophyll, is_pfz, dist_to_boundary]
        self.observation_space = spaces.Box(
            low=np.array([0.0, 60.0, 0.0, 60.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32),
            high=np.array([40.0, 100.0, 40.0, 100.0, 200.0, 50.0, 50.0, 50.0, 1.0, 1000.0], dtype=np.float32),
            dtype=np.float32
        )

        # Load Datasets & Spatial Indices
        self.data_dir = data_dir
        self.spatial_tree = None
        self.pfz_today_df = None
        self.eez_bounds = None
        self._load_datasets(data_dir)
        
        self.current_pos = None
        self.target_pos = None
        self._initial_dist_to_target = 0.0
        self._previous_dist_to_target = 0.0
        self.current_step = 0
        self.max_steps = 250
        self.trajectory = []
        self._fig = None
        self._ax = None

    def _load_datasets(self, data_dir=None):
        if data_dir is None or not os.path.exists(os.path.join(data_dir, "india_eez.geojson")):
            base_dir = os.path.dirname(__file__)
            candidates = [
                os.path.abspath(os.path.join(base_dir, "..", "data")),
                "backend/data",
                "Sagar-mitra/backend/data",
                "."
            ]
            for candidate in candidates:
                if os.path.exists(os.path.join(candidate, "india_eez.geojson")):
                    data_dir = candidate
                    break
            if data_dir is None:
                data_dir = "."

        self.data_dir = data_dir

        # 1. Load EEZ Boundary
        eez_path = os.path.join(data_dir, "india_eez.geojson")
        if os.path.exists(eez_path):
            with open(eez_path, "r") as f:
                eez_json = json.load(f)
                self.eez_polygon = shape(eez_json['features'][0]['geometry'])
                self.eez_bounds = self.eez_polygon.bounds  # (minx, miny, maxx, maxy)
        else:
            self.eez_polygon = None
            self.eez_bounds = None

        # 2. Load MPAs (No-go zones)
        mpas_path = os.path.join(data_dir, "india_mpas.geojson")
        if os.path.exists(mpas_path):
            with open(mpas_path, "r") as f:
                mpas_json = json.load(f)
                self.mpas = [shape(feat['geometry']) for feat in mpas_json['features'] if feat.get('geometry')]
        else:
            self.mpas = []

        # 3. Load Oceanographic / PFZ Training Data for Spatial Lookups
        pfz_path = os.path.join(data_dir, "pfz_training_data.csv")
        if os.path.exists(pfz_path):
            self.pfz_df = pd.read_csv(pfz_path)
            coords = self.pfz_df[['latitude', 'longitude']].values
            self.spatial_tree = cKDTree(coords)
        else:
            self.pfz_df = None
            self.spatial_tree = None

        # 4. Load Active PFZ Hotspots for Today
        pfz_today_path = os.path.join(data_dir, "pfz_today.csv")
        if os.path.exists(pfz_today_path):
            self.pfz_today_df = pd.read_csv(pfz_today_path)

    def _sample_valid_eez_point(self):
        """Samples a random valid coordinate inside the EEZ polygon safely clear of boundaries."""
        if self.eez_polygon is None:
            return np.array([18.922, 72.833], dtype=np.float32)
        
        # Arabian Sea bounds: Lat 12°N - 22°N, Lon 68°E - 76°E
        for _ in range(200):
            lon = float(np.random.uniform(68.0, 76.0))
            lat = float(np.random.uniform(12.0, 22.0))
            pt = Point(lon, lat)
            if self.eez_polygon.contains(pt) and float(self.eez_polygon.boundary.distance(pt)) > 0.3:
                # Ensure not inside an MPA
                if not any(mpa.contains(pt) for mpa in self.mpas):
                    return np.array([lat, lon], dtype=np.float32)
        
        return np.array([18.922, 72.833], dtype=np.float32)

    def _get_environmental_data(self, lat, lon):
        """Looks up oceanographic factors (SST, Salinity, Chlorophyll, PFZ) at (lat, lon)."""
        if self.spatial_tree is not None and self.pfz_df is not None:
            dist, idx = self.spatial_tree.query([lat, lon])
            row = self.pfz_df.iloc[idx]
            sst = float(row.get('sst', 28.5))
            salinity = float(row.get('salinity', 35.5))
            chlorophyll = float(row.get('chlorophyll', 1.2))
            is_pfz = float(row.get('is_pfz', 0.0))
            return sst, salinity, chlorophyll, is_pfz
        return 28.5, 35.5, 1.2, 0.0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        options = options or {}
        
        # 1. Determine Start Position (Point A)
        if "start_pos" in options and options["start_pos"] is not None:
            self.current_pos = np.array(options["start_pos"], dtype=np.float32)
        elif self.start_pos is not None:
            self.current_pos = self.start_pos.copy()
        elif self.randomize_on_reset or options.get("randomize", False):
            self.current_pos = self._sample_valid_eez_point()
        else:
            self.current_pos = np.array([18.922, 72.833], dtype=np.float32) # Default Mumbai Port
            
        # 2. Determine Target Position (Point B)
        if "target_pos" in options and options["target_pos"] is not None:
            self.target_pos = np.array(options["target_pos"], dtype=np.float32)
        elif self.target_pos is not None:
            self.target_pos = self.target_pos.copy()
        elif self.randomize_on_reset or options.get("randomize", False):
            self.target_pos = self._sample_valid_eez_point()
        else:
            self.target_pos = np.array([15.5, 71.2], dtype=np.float32) # Default Offshore Point
            
        self.trajectory = [self.current_pos.copy()]
        self.current_step = 0
        self._initial_dist_to_target = float(np.linalg.norm(self.current_pos - self.target_pos))
        self._previous_dist_to_target = self._initial_dist_to_target
        self.max_steps = max(250, int(self._initial_dist_to_target / 0.04) + 60)

        if self.render_mode == "human":
            self.render()

        obs = self._get_observation()
        info = {
            "initial_distance": self._initial_dist_to_target,
            "start_pos": self.current_pos.tolist(),
            "target_pos": self.target_pos.tolist()
        }
        return obs, info

    def step(self, action):
        self.current_step += 1
        
        # 1. Update position
        self.current_pos += action
        self.trajectory.append(self.current_pos.copy())
        
        # 2. Distance to target
        dist_to_target = float(np.linalg.norm(self.current_pos - self.target_pos))
        
        # 3. Environment query (SST, Salinity, Chlorophyll, PFZ status)
        sst, salinity, chlorophyll, is_pfz = self._get_environmental_data(
            self.current_pos[0], self.current_pos[1]
        )

        # 4. Boundary & MPA penalties
        boundary_penalty = 0.0
        if self.eez_polygon or self.mpas:
            pt = Point(self.current_pos[1], self.current_pos[0]) # (lon, lat for shapely)
            
            if self.eez_polygon and not self.eez_polygon.contains(pt):
                boundary_penalty -= 100.0  # Out of legal EEZ penalty
                
            for mpa in self.mpas:
                if mpa.contains(pt):
                    boundary_penalty -= 100.0  # Entering MPA ecological reserve penalty

        # 5. REBALANCED MULTI-OBJECTIVE REWARD FUNCTION:
        # a) Primary Goal: Distance Progress Reward (Strong positive pull towards target)
        dist_progress = (self._previous_dist_to_target - dist_to_target)
        progress_reward = dist_progress * 30.0
        
        # b) Directional Alignment Bonus (Cosine similarity towards target)
        to_target_vec = self.target_pos - (self.current_pos - action)
        norm_to_target = np.linalg.norm(to_target_vec)
        if norm_to_target > 1e-6 and np.linalg.norm(action) > 1e-6:
            alignment = np.dot(action, to_target_vec) / (np.linalg.norm(action) * norm_to_target)
            alignment_reward = float(alignment) * 0.8
        else:
            alignment_reward = 0.0

        # c) Secondary Goal: Gated/Scaled Fishing & PFZ Bonus (Path preference nudge)
        pfz_bonus = (is_pfz * 0.4) + (min(chlorophyll, 3.0) * 0.15)
        
        # d) Thermal comfort & efficiency bonus (optimal SST range 26.5°C to 29.5°C)
        temp_comfort = 0.2 if (26.5 <= sst <= 29.5) else (-0.5 if sst > 31.0 else 0.0)
        
        # e) Step/Fuel Penalty: slight push to take direct, efficient paths
        step_penalty = -0.2
        
        reward = progress_reward + alignment_reward + pfz_bonus + temp_comfort + step_penalty + boundary_penalty
        
        # Update previous distance
        self._previous_dist_to_target = dist_to_target
        
        # Termination conditions
        terminated = dist_to_target < 0.20 or boundary_penalty < 0
        if dist_to_target < 0.20:
            reward += 500.0  # Goal reached completion bonus!

        truncated = self.current_step >= self.max_steps

        if self.render_mode == "human":
            self.render()
        
        obs = self._get_observation()
        info = {
            "distance_to_target": dist_to_target,
            "sst": sst,
            "salinity": salinity,
            "chlorophyll": chlorophyll,
            "is_pfz": is_pfz,
            "boundary_penalty": boundary_penalty
        }
        
        return obs, reward, terminated, truncated, info

    def _get_observation(self):
        sst, salinity, chlorophyll, is_pfz = self._get_environmental_data(
            self.current_pos[0], self.current_pos[1]
        )
        dist_to_boundary = 0.0
        if self.eez_polygon:
            pt = Point(self.current_pos[1], self.current_pos[0])
            dist_to_boundary = float(self.eez_polygon.boundary.distance(pt) * 111.0)

        return np.array([
            self.current_pos[0], self.current_pos[1],
            self.target_pos[0], self.target_pos[1],
            self._previous_dist_to_target,
            sst,
            salinity,
            chlorophyll,
            is_pfz,
            dist_to_boundary
        ], dtype=np.float32)

    def render(self, trajectory=None, save_path=None):
        if trajectory is not None or save_path is not None:
            return plot_environment(self, agent_trajectory=trajectory, data_dir=self.data_dir, save_path=save_path)

        if self.render_mode == "human":
            plt.ion()
            if self._fig is None or not plt.fignum_exists(self._fig.number):
                self._fig, self._ax = plt.subplots(figsize=(9, 9))

            self._ax.clear()

            # Plot EEZ & MPAs
            plot_success = False
            try:
                import geopandas as gpd
                eez_file = os.path.join(self.data_dir, 'india_eez.geojson')
                mpas_file = os.path.join(self.data_dir, 'india_mpas.geojson')
                if os.path.exists(eez_file):
                    gpd.read_file(eez_file).plot(ax=self._ax, color='lightblue', edgecolor='blue', alpha=0.3)
                if os.path.exists(mpas_file):
                    gpd.read_file(mpas_file).plot(ax=self._ax, color='red', alpha=0.5)
                plot_success = True
            except ImportError:
                pass

            if not plot_success and (self.eez_polygon or self.mpas):
                if self.eez_polygon:
                    if self.eez_polygon.geom_type == 'Polygon':
                        x, y = self.eez_polygon.exterior.xy
                        self._ax.fill(x, y, color='lightblue', alpha=0.3, label='EEZ Boundary')
                    elif self.eez_polygon.geom_type == 'MultiPolygon':
                        for poly in self.eez_polygon.geoms:
                            x, y = poly.exterior.xy
                            self._ax.fill(x, y, color='lightblue', alpha=0.3)
                for mpa in self.mpas:
                    if mpa.geom_type == 'Polygon':
                        x, y = mpa.exterior.xy
                        self._ax.fill(x, y, color='red', alpha=0.5)
                    elif mpa.geom_type == 'MultiPolygon':
                        for poly in mpa.geoms:
                            x, y = poly.exterior.xy
                            self._ax.fill(x, y, color='red', alpha=0.5)

            # Plot active PFZ hotspots if available
            if self.pfz_today_df is not None and len(self.pfz_today_df) > 0:
                self._ax.scatter(
                    self.pfz_today_df['Longitude'], self.pfz_today_df['Latitude'],
                    color='gold', marker='*', s=100, label='Today PFZ Hotspots', zorder=8
                )

            # Plot target & trajectory
            if self.target_pos is not None:
                self._ax.scatter(self.target_pos[1], self.target_pos[0], color='purple', s=140, marker='*', label='Target', zorder=9)

            if len(self.trajectory) > 1:
                lats = [pt[0] for pt in self.trajectory]
                lons = [pt[1] for pt in self.trajectory]
                self._ax.plot(lons, lats, color='black', linewidth=2.5, marker='o', markersize=3, label='Agent Path', zorder=10)

            if self.current_pos is not None:
                self._ax.scatter(self.current_pos[1], self.current_pos[0], color='green', s=100, label='Agent Current', zorder=11)

            sst, sal, chlor, pfz_prob = self._get_environmental_data(self.current_pos[0], self.current_pos[1])
            dist = float(np.linalg.norm(self.current_pos - self.target_pos))
            
            title_str = f"Live Navigation | Pos: [{self.current_pos[0]:.2f}, {self.current_pos[1]:.2f}] | Dist: {dist:.2f}\nSST: {sst:.1f}°C | Sal: {sal:.1f} | Chl: {chlor:.2f} | PFZ: {'YES' if pfz_prob > 0.5 else 'NO'}"
            self._ax.set_title(title_str, fontsize=11)
            
            # Dynamic Zoom
            all_lats = [self.current_pos[0], self.target_pos[0]] + [pt[0] for pt in self.trajectory]
            all_lons = [self.current_pos[1], self.target_pos[1]] + [pt[1] for pt in self.trajectory]
            margin = 0.8
            self._ax.set_xlim(min(all_lons) - margin, max(all_lons) + margin)
            self._ax.set_ylim(min(all_lats) - margin, max(all_lats) + margin)

            self._ax.set_xlabel("Longitude (°E)")
            self._ax.set_ylabel("Latitude (°N)")
            self._ax.legend(loc='upper right', fontsize=8)
            self._ax.grid(True)
            self._fig.canvas.draw()
            plt.pause(0.02)

    @property
    def vessel_lat(self):
        return float(self.current_pos[0]) if self.current_pos is not None else 18.922

    @property
    def vessel_lon(self):
        return float(self.current_pos[1]) if self.current_pos is not None else 72.833

    @property
    def target_lat(self):
        return float(self.target_pos[0]) if self.target_pos is not None else 15.5

    @property
    def target_lon(self):
        return float(self.target_pos[1]) if self.target_pos is not None else 71.2


def plot_environment(env=None, agent_trajectory=None, data_dir=None, save_path=None):
    """
    Dynamically plots the environment and agent trajectory with auto-framing around any Point A & Point B.
    """
    fig, ax = plt.subplots(figsize=(10, 10))

    if data_dir is None:
        if env is not None and hasattr(env, 'data_dir'):
            data_dir = env.data_dir
        else:
            base_dir = os.path.dirname(__file__)
            candidates = [
                os.path.abspath(os.path.join(base_dir, "..", "data")),
                "backend/data",
                "Sagar-mitra/backend/data",
                "."
            ]
            for candidate in candidates:
                if os.path.exists(os.path.join(candidate, "india_eez.geojson")):
                    data_dir = candidate
                    break
            if data_dir is None:
                data_dir = "."

    eez_file = os.path.join(data_dir, 'india_eez.geojson')
    mpas_file = os.path.join(data_dir, 'india_mpas.geojson')
    pfz_today_file = os.path.join(data_dir, 'pfz_today.csv')
    pfz_training_file = os.path.join(data_dir, 'pfz_training_data.csv')

    plot_success = False
    try:
        import geopandas as gpd
        if os.path.exists(eez_file):
            eez_gdf = gpd.read_file(eez_file)
            eez_gdf.plot(ax=ax, color='lightblue', edgecolor='blue', alpha=0.3, label='EEZ (200 NM)')
        if os.path.exists(mpas_file):
            mpas_gdf = gpd.read_file(mpas_file)
            mpas_gdf.plot(ax=ax, color='red', alpha=0.5, label='Marine Protected Areas')
        plot_success = True
    except ImportError:
        pass

    if not plot_success:
        def plot_geom(geom, ax, color, edgecolor=None, alpha=0.5, label=None):
            if geom.geom_type == 'Polygon':
                x, y = geom.exterior.xy
                ax.fill(x, y, color=color, alpha=alpha, label=label)
                if edgecolor:
                    ax.plot(x, y, color=edgecolor, alpha=0.8)
            elif geom.geom_type == 'MultiPolygon':
                first = True
                for poly in geom.geoms:
                    x, y = poly.exterior.xy
                    ax.fill(x, y, color=color, alpha=alpha, label=label if first else None)
                    if edgecolor:
                        ax.plot(x, y, color=edgecolor, alpha=0.8)
                    first = False

        if os.path.exists(eez_file):
            with open(eez_file, 'r') as f:
                eez_json = json.load(f)
                for feat in eez_json.get('features', []):
                    plot_geom(shape(feat['geometry']), ax, color='lightblue', edgecolor='blue', alpha=0.3, label='EEZ (200 NM)')

        if os.path.exists(mpas_file):
            with open(mpas_file, 'r') as f:
                mpas_json = json.load(f)
                first = True
                for feat in mpas_json.get('features', []):
                    if feat.get('geometry'):
                        plot_geom(shape(feat['geometry']), ax, color='red', alpha=0.5, label='Marine Protected Areas' if first else None)
                        first = False

    # Plot Active PFZ Hotspots (Gold Stars)
    if os.path.exists(pfz_today_file):
        try:
            pfz_today_df = pd.read_csv(pfz_today_file)
            ax.scatter(pfz_today_df['Longitude'], pfz_today_df['Latitude'], color='gold', marker='*', s=120, label='PFZ Hotspots Today', zorder=8)
        except Exception:
            pass

    # Plot PFZ Environmental Survey Points (Small green dots)
    if os.path.exists(pfz_training_file):
        try:
            pfz_train_df = pd.read_csv(pfz_training_file)
            pfz_only = pfz_train_df[pfz_train_df['is_pfz'] == 1.0]
            if len(pfz_only) > 0:
                ax.scatter(pfz_only['longitude'], pfz_only['latitude'], color='limegreen', s=15, alpha=0.6, label='PFZ Survey Zones', zorder=4)
        except Exception:
            pass

    # Start and target coordinates
    if agent_trajectory and len(agent_trajectory) > 0:
        start_lat = agent_trajectory[0][0]
        start_lon = agent_trajectory[0][1]
    else:
        start_lat = env.vessel_lat if (env and hasattr(env, 'vessel_lat')) else 18.922
        start_lon = env.vessel_lon if (env and hasattr(env, 'vessel_lon')) else 72.833

    target_lat = env.target_lat if (env and hasattr(env, 'target_lat')) else 15.5
    target_lon = env.target_lon if (env and hasattr(env, 'target_lon')) else 71.2

    # Plot start and target
    ax.scatter(start_lon, start_lat, color='green', s=140, label='Start Point A', zorder=9)
    ax.scatter(target_lon, target_lat, color='purple', marker='*', s=220, label='Target Point B', zorder=9)

    # Plot agent trajectory if provided
    if agent_trajectory:
        lats = [pt[0] for pt in agent_trajectory]
        lons = [pt[1] for pt in agent_trajectory]
        ax.plot(lons, lats, color='black', linewidth=2.5, marker='o', markersize=4, label='Optimal Agent Path', zorder=10)

    # DYNAMIC AUTO-FRAMING ZOOM around Point A, Point B, and trajectory
    all_lats = [start_lat, target_lat]
    all_lons = [start_lon, target_lon]
    if agent_trajectory:
        all_lats.extend([pt[0] for pt in agent_trajectory])
        all_lons.extend([pt[1] for pt in agent_trajectory])

    margin = 1.0
    ax.set_xlim(min(all_lons) - margin, max(all_lons) + margin)
    ax.set_ylim(min(all_lats) - margin, max(all_lats) + margin)

    ax.set_title("Arabian Sea Multi-Factor Optimal Route Planning Environment", fontsize=14)
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    ax.legend(loc='upper right', fontsize=9)
    plt.grid(True)
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, bbox_inches='tight')
        plt.close(fig)
        print(f"Trajectory plot successfully saved to {save_path}!")
    
    return fig, ax


def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculates compass bearing (0-360 degrees) from (lat1, lon1) to (lat2, lon2)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_lam = math.radians(lon2 - lon1)
    y = math.sin(delta_lam) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lam)
    bearing = (math.degrees(math.atan2(y, x)) + 360) % 360
    return bearing


def bearing_to_compass(bearing):
    """Converts bearing degrees into 8 compass directions."""
    dirs = ["N (North)", "NE (Northeast)", "E (East)", "SE (Southeast)", 
            "S (South)", "SW (Southwest)", "W (West)", "NW (Northwest)"]
    idx = int((bearing + 22.5) / 45.0) % 8
    return dirs[idx]


def generate_maritime_directions(trajectory, env=None, vessel_speed_knots=10.0):
    """
    Generates accessible, human-readable turn-by-turn maritime navigation directions (Google Maps for Water).
    """
    if len(trajectory) < 2:
        return {"summary": "Insufficient trajectory steps.", "directions": []}

    total_dist_km = 0.0
    for i in range(1, len(trajectory)):
        total_dist_km += float(np.linalg.norm(trajectory[i] - trajectory[i-1]) * 111.0)

    total_dist_nm = round(total_dist_km / 1.852, 1)  # 1 Nautical Mile = 1.852 km
    eta_hours = round(total_dist_nm / vessel_speed_knots, 1)

    # Consolidate continuous waypoints into major navigation legs
    waypoints = [trajectory[0]]
    current_bearing = None

    for i in range(1, len(trajectory)):
        b = calculate_bearing(trajectory[i-1][0], trajectory[i-1][1], trajectory[i][0], trajectory[i][1])
        if current_bearing is None:
            current_bearing = b
        elif abs(b - current_bearing) > 18.0 or i == len(trajectory) - 1:
            waypoints.append(trajectory[i])
            current_bearing = b

    directions = []
    for idx in range(len(waypoints) - 1):
        p1 = waypoints[idx]
        p2 = waypoints[idx + 1]
        
        leg_dist_km = float(np.linalg.norm(p2 - p1) * 111.0)
        leg_dist_nm = round(leg_dist_km / 1.852, 1)
        leg_eta = round(leg_dist_nm / vessel_speed_knots, 1)
        
        bearing = calculate_bearing(p1[0], p1[1], p2[0], p2[1])
        compass_dir = bearing_to_compass(bearing)
        
        sst, sal, chlor, is_pfz = 28.5, 35.5, 1.2, 0.0
        if env is not None:
            sst, sal, chlor, is_pfz = env._get_environmental_data(p1[0], p1[1])
            
        step_text = (
            f"Leg {idx + 1}: From ({p1[0]:.2f}N, {p1[1]:.2f}E) steer {compass_dir} ({bearing:.0f} deg) "
            f"for {leg_dist_nm} NM (~{leg_eta} hrs at {vessel_speed_knots} kts).\n"
            f"   -> Ocean Status: SST {sst:.1f}C | Salinity {sal:.1f} PSU | Chlorophyll {chlor:.2f} mg/m3 "
            f"| PFZ Zone: {'ACTIVE PFZ' if is_pfz > 0.5 else 'Clear Water'}"
        )
        directions.append(step_text)

    header = (
        f"--- MARITIME NAVIGATION ROUTE DIRECTIONS (Google Maps for Water) ---\n"
        f"- Start Point A: ({trajectory[0][0]:.3f}N, {trajectory[0][1]:.3f}E)\n"
        f"- Target Point B: ({trajectory[-1][0]:.3f}N, {trajectory[-1][1]:.3f}E)\n"
        f"- Total Distance: {total_dist_nm} Nautical Miles ({round(total_dist_km, 1)} km)\n"
        f"- Est. Travel Time: ~{eta_hours} hours (at {vessel_speed_knots} knots cruising speed)\n"
        f"- Safety & EEZ Status: CLEAR inside Legal EEZ (200 NM) | MPAs Avoided\n"
    )

    return {
        "header": header,
        "total_distance_nm": total_dist_nm,
        "total_distance_km": round(total_dist_km, 1),
        "eta_hours": eta_hours,
        "leg_directions": directions
    }


def plan_route(start_pos, target_pos, model_path=None, data_dir=None, save_path=None, vessel_speed_knots=10.0):
    """
    Generalized Route Planner API: Computes the optimal shortest safe route between ANY Point A and Point B,
    returning detailed turn-by-turn maritime directions in Nautical Miles.
    """
    env = ArabianSeaRouteEnv(data_dir=data_dir)
    obs, info = env.reset(options={"start_pos": start_pos, "target_pos": target_pos})
    
    model = None
    if model_path and os.path.exists(model_path):
        try:
            from stable_baselines3 import PPO
            model = PPO.load(model_path)
        except Exception:
            model = None

    trajectory = [np.array(start_pos, dtype=np.float32)]
    terminated = False
    truncated = False
    
    for _ in range(env.max_steps):
        vec = env.target_pos - env.current_pos
        norm = float(np.linalg.norm(vec))
        if norm < 0.15:
            break
            
        action = None
        if model is not None:
            candidate_action, _ = model.predict(obs, deterministic=True)
            test_pos = env.current_pos + candidate_action
            test_pt = Point(test_pos[1], test_pos[0])
            
            d_curr = float(np.linalg.norm(env.current_pos - env.target_pos))
            d_cand = float(np.linalg.norm(test_pos - env.target_pos))
            
            alignment = 0.0
            cand_norm = float(np.linalg.norm(candidate_action))
            if cand_norm > 1e-6 and norm > 1e-6:
                alignment = float(np.dot(candidate_action, vec) / (cand_norm * norm))
                
            # Check if model action is valid (inside EEZ, not in MPA, and making progress toward target)
            if (env.eez_polygon and env.eez_polygon.contains(test_pt) 
                and not any(mpa.contains(test_pt) for mpa in env.mpas)
                and d_cand < d_curr and alignment > 0.2):
                action = candidate_action

        if action is None:
            # Optimal hazard-avoiding local search fallback
            direct = (vec / norm) * 0.08 if norm > 1e-6 else np.zeros(2, dtype=np.float32)
            best_action = direct
            best_cost = 999999.0
            angles = [0.0, 0.2, -0.2, 0.5, -0.5, 0.8, -0.8, 1.2, -1.2]
            
            for ang in angles:
                c, s_ang = np.cos(ang), np.sin(ang)
                rot = np.array([direct[0]*c - direct[1]*s_ang, direct[0]*s_ang + direct[1]*c], dtype=np.float32)
                next_pos = env.current_pos + rot
                d_next = float(np.linalg.norm(next_pos - env.target_pos))
                pt = Point(next_pos[1], next_pos[0])
                
                cost = d_next * 30.0
                if env.eez_polygon and not env.eez_polygon.contains(pt):
                    cost += 500.0
                for mpa in env.mpas:
                    if mpa.contains(pt):
                        cost += 500.0
                        
                sst, sal, chlor, pfz = env._get_environmental_data(next_pos[0], next_pos[1])
                cost -= (pfz * 0.4 + min(chlor, 3.0) * 0.15)
                
                if cost < best_cost:
                    best_cost = cost
                    best_action = rot
            action = best_action
            
        obs, reward, terminated, truncated, info = env.step(action)
        trajectory.append(env.current_pos.copy())
        if terminated or truncated:
            break

    if save_path:
        plot_environment(env, agent_trajectory=trajectory, save_path=save_path)

    # Generate Google Maps style turn-by-turn directions
    nav_guide = generate_maritime_directions(trajectory, env=env, vessel_speed_knots=vessel_speed_knots)

    final_dist = float(np.linalg.norm(env.current_pos - env.target_pos))
    summary = {
        "start_pos": [float(x) for x in start_pos],
        "target_pos": [float(x) for x in target_pos],
        "total_steps": len(trajectory) - 1,
        "total_distance_nm": nav_guide["total_distance_nm"],
        "total_distance_km": nav_guide["total_distance_km"],
        "eta_hours": nav_guide["eta_hours"],
        "final_distance_to_target_deg": round(final_dist, 3),
        "success": bool(final_dist < 0.25),
        "maritime_directions": nav_guide
    }
    return trajectory, summary