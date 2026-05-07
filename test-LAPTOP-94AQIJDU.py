import numpy as np
import matplotlib.pyplot as plt

def plot_evaporation_rate(
    T_min_C=-50, T_max_C=20, n_points=500,
    alpha=1.0,
    L=2.26e3, #J/g
    R=8.314,
    C=20.50,
    m=18.0152,
    k=1.38e-23
):
    """
    Plot evaporation rate J and saturation pressure P_sat vs temperature (°C)
    """

    # Temperature
    T_C = np.linspace(T_min_C, T_max_C, n_points)
    T_K = T_C + 273.15

    # Clausius-Clapeyron
    
    P_sat = clausius_clapeyron(T_K, L, R, C)
    P_vap = august_roche_magnus(T_C)
    
    print(P_vap)
    print(P_sat)
    
    # Hertz-Knudsen
    J = alpha * (P_sat - P_vap) / np.sqrt(2 * np.pi * m * k * T_K)

    # ----------------------------
    # Plot
    # ----------------------------
    fig, ax1 = plt.subplots()

    # Left axis → evaporation rate
    ax1.plot(T_C, J)
    ax1.set_xlabel("Temperature (°C)")
    ax1.set_ylabel("Evaporation rate J")
    ax1.grid()

    # Right axis → saturation pressure
    ax2 = ax1.twinx()
    ax2.plot(T_C, P_sat, linestyle="--")
    ax2.plot(T_C, P_vap, linestyle="--")
    ax2.set_ylabel("Saturation pressure $P_{sat}$ (Pa)")
    # ax2.set_yscale("log")

    plt.title("Evaporation Rate and Saturation Pressure vs Temperature")

    plt.show()

def clausius_clapeyron(T, L, R, C):
    return np.exp(- (L / R) * (1 / T) + C)

def august_roche_magnus(T):
    return 610.94 * np.exp((17.625 * T) / (T + 243.04)) # Alduchov and Eskridge, 1996

# Run it
plot_evaporation_rate()