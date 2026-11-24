# Flight Path Generator

<img src="icon.svg" alt="Flight Path Generator Icon" width="64" />

A QGIS plugin that generates parallel North–South survey flight lines (for **SPECIM AFX**) and a continuous connected flight path (for **DJI Pilot**) from a selected polygon feature.

---

## Features

- **CRS-Agnostic Metric Calculations**: Automatically builds a local orthographic projection (`+proj=ortho`) centered on the selected polygon's centroid so spacing, overshoot, and buffering are calculated accurately in meters regardless of the source layer's CRS.
- **Dual Output Formats**:
  - **SPECIM AFX Flight Lines**: Parallel N–S lines clipped to the (optionally buffered) polygon boundary, named `fl1`, `fl2`, …
  - **DJI Pilot Continuous Path**: Alternating South → North / North → South connected wayline with configurable line-end overshoot, altitude, and flight speed metadata (`mis:autoFlightSpeed`, `mis:altitude`).
- **Live QGIS Preview**: Adds both generated layers directly to the active QGIS map canvas as temporary memory layers.
- **KML Export**: Optionally exports WGS84 (`EPSG:4326`) KML files ready for mission planning software.

---

## Requirements

- **QGIS**: Version 3.0 – 4.x (no external Python packages required beyond standard QGIS / PyQt libraries).

---

## Installation

### Option 1: Install from ZIP (Recommended)

1. Download this repository as a `.zip` file (ensure the top-level folder inside the ZIP is named `flight_path_generator`).
2. In QGIS, go to **Plugins → Manage and Install Plugins…**
3. Select **Install from ZIP**, choose the downloaded archive, and click **Install Plugin**.

### Option 2: Manual / Git Clone

Clone or copy the `flight_path_generator` folder into your QGIS profile's `python/plugins` directory:

- **Windows**: `C:\Users\<username>\AppData\Roaming\QGIS\QGIS4\profiles\default\python\plugins\flight_path_generator` *(or `QGIS3` for QGIS 3.x)*
- **macOS**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/flight_path_generator`
- **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/flight_path_generator`

Restart QGIS and enable **Flight Path Generator** under **Plugins → Manage and Install Plugins… → Installed**.

---

## Usage

1. Select a **polygon vector layer** in the QGIS Layers panel.
2. Select a **polygon feature** on the map canvas (if multiple features are selected, the first selected feature is used).
3. Launch the plugin from the **toolbar icon** or via **Plugins → Flight Path Generator**.
4. Configure the flight parameters and (optionally) choose an output folder and filename base.
5. Click **Generate**.

### Configuration Parameters

| Parameter | Default | Range | Description |
| :--- | :---: | :---: | :--- |
| **Line Spacing (meters)** | `15.0` | `1.0` – `1000.0` | Horizontal distance between parallel N–S flight lines. |
| **Overshoot (meters)** | `10.0` | `0.0` – `1000.0` | Extension added past the north and south polygon boundaries for the continuous DJI path. |
| **Polygon Buffer (meters)** | `0.0` | `-1000.0` – `1000.0` | Positive values expand the survey polygon; negative values shrink it before generating lines. |
| **Altitude (meters)** | `80.0` | `1.0` – `1000.0` | Flight altitude (`relativeToGround`) written to the DJI path KML. |
| **Speed (m/s)** | `5.0` | `0.1` – `100.0` | Auto flight speed written to the DJI path KML. |
| **Output Directory** | *(empty)* | — | Optional directory for KML export. Leave blank to only add layers to the QGIS canvas. |
| **Filename Base** | `Flight_Path` | — | Prefix used for both QGIS memory layers and exported KML files. |

---

## Outputs

### QGIS Map Canvas Layers

- **`<Filename Base>_AFX_Lines`** (`MultiLineString` memory layer) — Parallel N–S flight lines with a `name` attribute (`fl1`, `fl2`, …).
- **`<Filename Base>_DJI_Path`** (`LineString` memory layer) — Single continuous boustrophedon flight path including overshoots.

### Exported KML Files *(when an output directory is specified)*

- **`<Filename Base>_lines.kml`** — Individual flight line placemarks (`fl1`, `fl2`, …) styled in yellow for SPECIM AFX.
- **`<Filename Base>_path.kml`** — Continuous flight path styled in red with `relativeToGround` altitude and DJI `ExtendedData` (`mis:autoFlightSpeed` and `mis:altitude`) for DJI Pilot.

---

## Repository Structure

```text
flight_path_generator/
├── __init__.py      # QGIS plugin entry point (classFactory)
├── plugin.py        # UI dialog, flight path geometry calculations, and KML export
├── metadata.txt     # QGIS plugin metadata
├── icon.svg         # Plugin toolbar & manager icon
└── README.md        # Documentation
```

---

## Author

**Tim Whiteside**  
Email: `tim.whiteside@dcceew.gov.au`
