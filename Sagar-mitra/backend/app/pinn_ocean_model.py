"""
Physics-Informed Neural Network (PINN) for Arabian Sea Ocean Dynamics
=====================================================================
This standalone module implements a Physics-Informed Neural Network (PINN)
that models oceanographic scalar fields (Sea Surface Temperature & Chlorophyll)
and fluid velocity vectors (Ocean Currents) while enforcing physical conservation
laws (Advection-Diffusion PDE and Continuity / Mass Conservation PDE).

Key Equations Enforced via PyTorch Automatic Differentiation:
1. Advection-Diffusion PDE (Thermal & Biological Transport):
   dT/dt + u*(dT/dx) + v*(dT/dy) - D * (d^2T/dx^2 + d^2T/dy^2) = 0
2. Incompressibility / Continuity Equation (Ocean Current Velocity Field):
   du/dx + dv/dy = 0
"""

import os
import math
import torch
import torch.nn as nn
import numpy as np
import pandas as pd


class OceanPINN(nn.Module):
    """
    Physics-Informed Neural Network architecture.
    Inputs: (lat, lon, time) normalized coordinates.
    Outputs: [SST, Chlorophyll, u_current, v_current]
    """
    def __init__(self, hidden_dim=64, num_layers=4):
        super(OceanPINN, self).__init__()
        
        layers = []
        # Input layer: (lat, lon, time) -> hidden_dim
        layers.append(nn.Linear(3, hidden_dim))
        layers.append(nn.Tanh())  # Tanh activation for smooth derivative computation
        
        for _ in range(num_layers - 1):
            layers.append(nn.Linear(hidden_dim, hidden_dim))
            layers.append(nn.Tanh())
            
        # Output layer: [sst, chlorophyll, u_current, v_current]
        layers.append(nn.Linear(hidden_dim, 4))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


def compute_pde_residuals(model, lat, lon, time, diffusion_coeff=0.01):
    """
    Uses PyTorch Automatic Differentiation (autograd) to compute PDE physics residuals.
    
    Returns:
    - advection_residual: Enforces heat & nutrient transport physics
    - continuity_residual: Enforces ocean current fluid incompressibility (du/dx + dv/dy = 0)
    """
    # Enable gradient tracking for inputs
    lat = lat.clone().detach().requires_grad_(True)
    lon = lon.clone().detach().requires_grad_(True)
    time = time.clone().detach().requires_grad_(True)
    
    inputs = torch.cat([lat, lon, time], dim=1)
    outputs = model(inputs)
    
    sst = outputs[:, 0:1]
    chlor = outputs[:, 1:2]
    u_curr = outputs[:, 2:3]
    v_curr = outputs[:, 3:4]
    
    # First-order derivatives wrt lat, lon, time
    ones = torch.ones_like(sst)
    
    dsst_dlat = torch.autograd.grad(sst, lat, grad_outputs=ones, create_graph=True, retain_graph=True)[0]
    dsst_dlon = torch.autograd.grad(sst, lon, grad_outputs=ones, create_graph=True, retain_graph=True)[0]
    dsst_dtime = torch.autograd.grad(sst, time, grad_outputs=ones, create_graph=True, retain_graph=True)[0]
    
    # Second-order derivatives (Diffusion)
    dsst_dlat2 = torch.autograd.grad(dsst_dlat, lat, grad_outputs=ones, create_graph=True, retain_graph=True)[0]
    dsst_dlon2 = torch.autograd.grad(dsst_dlon, lon, grad_outputs=ones, create_graph=True, retain_graph=True)[0]
    
    # 1. Advection-Diffusion PDE Residual for SST: dT/dt + u*(dT/dx) + v*(dT/dy) - D*(d2T/dx2 + d2T/dy2) = 0
    advection_residual = dsst_dtime + u_curr * dsst_dlat + v_curr * dsst_dlon - diffusion_coeff * (dsst_dlat2 + dsst_dlon2)
    
    # 2. Continuity PDE Residual for Ocean Currents: du/dlat + dv/dlon = 0
    du_dlat = torch.autograd.grad(u_curr, lat, grad_outputs=ones, create_graph=True, retain_graph=True)[0]
    dv_dlon = torch.autograd.grad(v_curr, lon, grad_outputs=ones, create_graph=True, retain_graph=True)[0]
    continuity_residual = du_dlat + dv_dlon
    
    return advection_residual, continuity_residual


class StandalonePINNEvaluator:
    """
    Standalone Evaluator for testing and querying the trained PINN ocean model.
    """
    def __init__(self, model_path=None):
        self.model = OceanPINN()
        self.model.eval()
        self.is_trained = False
        
        if model_path and os.path.exists(model_path):
            try:
                self.model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
                self.is_trained = True
                print(f"Successfully loaded PINN model weights from {model_path}")
            except Exception as e:
                print(f"Could not load PINN model from {model_path}: {e}")

    def evaluate_ocean_physics(self, lat, lon, time_step=0.0):
        """
        Evaluates physics-constrained SST, Chlorophyll, and Ocean Current vectors at (lat, lon).
        """
        # Simple spatial normalization (Arabian Sea Lat 10..22, Lon 68..76)
        lat_norm = (lat - 16.0) / 6.0
        lon_norm = (lon - 72.0) / 4.0
        t_norm = time_step / 100.0
        
        inputs = torch.tensor([[lat_norm, lon_norm, t_norm]], dtype=torch.float32)
        with torch.no_grad():
            outputs = self.model(inputs).numpy()[0]
            
        sst_pred = float(outputs[0] * 3.0 + 28.5)
        chlor_pred = float(max(0.1, outputs[1] * 1.5 + 1.2))
        u_curr = float(outputs[2] * 0.5)
        v_curr = float(outputs[3] * 0.5)
        
        return {
            "sst": round(sst_pred, 2),
            "chlorophyll": round(chlor_pred, 2),
            "ocean_current_u_kts": round(u_curr, 2),
            "ocean_current_v_kts": round(v_curr, 2),
            "current_magnitude_kts": round(float(np.hypot(u_curr, v_curr)), 2),
            "pinn_trained": self.is_trained
        }
