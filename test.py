import numpy as np
import matplotlib.pyplot as plt

OFFSETS = [13.704, -2.8299, 27.852, -13.837] # blue, black, red, white
FIRST_COEFFICIENTS = [0.1612, 0.1097, 0.2452, 0.0076]
SECOND_COEFFICIENTS = [-3.0011, -1.1087, -5.1248, 1.3971]

# first, second, offset
FITS = [[0.125509,	-1.891261,	5.205203], # blue
[0.067673,	0.219476,	-16.208077], # black
[0.226843,	-4.587383,	23.984397], # red
[0.009988,	1.299066,	-12.197174]] # white

paths = [
    "C:/Users/jelme/OneDrive/Stage UT/camwatcher/data/compiled/05-19-09-06 - procent 0-1",
    "C:/Users/jelme/OneDrive/Stage UT/camwatcher/data/compiled/05-19-09-13 - procent 0-2",
    "C:/Users/jelme/OneDrive/Stage UT/camwatcher/data/compiled/05-19-09-20 - procent 0-3",
    "C:/Users/jelme/OneDrive/Stage UT/camwatcher/data/compiled/05-19-09-24 - procent 0-4",
    "C:/Users/jelme/OneDrive/Stage UT/camwatcher/data/compiled/05-19-09-27 - procent 0-5",
    "C:/Users/jelme/OneDrive/Stage UT/camwatcher/data/compiled/05-19-10-54 - procent 0-6",
    "C:/Users/jelme/OneDrive/Stage UT/camwatcher/data/compiled/05-19-10-59 - procent 0-7",
    "C:/Users/jelme/OneDrive/Stage UT/camwatcher/data/compiled/05-19-11-05 - procent 0-8",
    "C:/Users/jelme/OneDrive/Stage UT/camwatcher/data/compiled/05-19-11-11 - procent 0-9"
]

fig, axes = plt.subplots(5, 1, figsize=(12, 18))

for i in range(5):
    path = f"{paths[i]}/temperature.npz"

    data = np.load(path)

    timestamps = data['timestamps']
    temperatures = data['temperatures']

    first_temps_average = (
        sum(temperatures[0]) / len(temperatures[0])
    )

    offsets = temperatures[0] - first_temps_average

    new_temps = []

    for temps in temperatures:
        new_temps_snapshot = []

        for d in range(4):
            new_temps_snapshot.append(
                temps[d] - offsets[d]
            )

        new_temps.append(new_temps_snapshot)

    new_temps = np.array(new_temps)

    ax = axes[i]

    if new_temps.ndim == 2:
        for j in range(new_temps.shape[1]):
            ax.plot(
                timestamps,
                new_temps[:, j],
                label=f"T{j+1}"
            )
            ax.fill_between(
                timestamps,
                new_temps[:, j] - offsets[j],
                new_temps[:, j] + offsets[j],
                alpha=0.2
            )

        ax.legend()

    else:
        ax.plot(timestamps, new_temps)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Temperature")
    ax.set_title(f"Temperature vs Time #{i+1}")
    ax.grid()

plt.tight_layout()

plt.savefig("C:/Users/jelme/OneDrive/Stage UT/camwatcher/data/compiled/combined_temperature_plots.png")
plt.close()
            
            
            