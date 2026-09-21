# Minecraft World Mapper

A Python script that analyzes Minecraft world saves (Java Edition, **1.12 and earlier**) and renders a 2D top-down map as a PNG image.

Supports both the **Overworld** and the **Nether**, with optional height-based slicing and relief shading.

## Features

- **No Minecraft required** — reads `.mca` region files directly from disk
- **Overworld surface map** — top-down view with hill-shading based on block height
- **Nether support** — automatic `DIM-1` detection with height-slice mode to bypass the bedrock ceiling
- **Height slicing** — render a cross-section at any Y-level (great for cave maps and dungeon hunting)
- **Color palette** — 60+ block types mapped to colors, including wool, stained clay, and glass variants
- **Unknown block highlighting** — unmapped blocks appear in magenta so you can spot them easily
- **Progress output** — prints progress to the console while processing

## Screenshots

> Add your screenshots here — surface map, nether slice, underground cross-section.

## Requirements

- Python 3.7+
- [nbt](https://pypi.org/project/nbt/) — for reading Minecraft NBT/region files
- [Pillow](https://pypi.org/project/Pillow/) — for PNG output

## Installation

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install nbt Pillow
```

## Usage

```bash
python minecraft_map.py <world_dir> [options]
```

### Options

| Option        | Type  | Default     | Description                                                       |
|---------------|-------|-------------|-------------------------------------------------------------------|
| `--out`       | str   | `map.png`   | Output PNG file path                                              |
| `--mode`      | str   | `surface`   | Map mode: `surface` (with shading) or `top` (flat, no shading)   |
| `--nether`    | flag  | off         | Render the Nether (`DIM-1`). Sets default Y-slice to 32          |
| `--y`         | int   | none        | Render a cross-section at this Y-level instead of the surface     |
| `--no-shade`  | flag  | off         | Disable height-based shading (alias for `--mode top`)            |

### Examples

```bash
# Overworld surface map (default)
python minecraft_map.py /path/to/world --out overworld.png

# Overworld cross-section at Y=64
python minecraft_map.py /path/to/world --out caves.png --y 64

# Nether map (auto-slice at Y=32)
python minecraft_map.py /path/to/world --out nether.png --nether

# Nether map at a custom height
python minecraft_map.py /path/to/world --out nether.png --nether --y 50

# Flat map without shading
python minecraft_map.py /path/to/world --out flat.png --no-shade
```

### Finding your world folder

| OS      | Path                                                                 |
|---------|----------------------------------------------------------------------|
| Windows | `%APPDATA%\.minecraft\saves\<WorldName>`                            |
| macOS   | `~/Library/Application Support/minecraft/saves/<WorldName>`         |
| Linux   | `~/.minecraft/saves/<WorldName>`                                     |

For a **server** world, use the world directory directly (the one containing `region/`, `level.dat`, etc.).

## How It Works

1. **Scans** the `region/` (or `DIM-1/region/`) folder for `.mca` files
2. **Parses** each region file using the `nbt` library — extracts chunk sections, block arrays (`Blocks`, `Data`, `Add`)
3. **Finds the topmost block** in each column `(x, z)`, skipping transparent blocks (air, water, leaves, grass)
   — or takes the block at a fixed Y-level in slice mode
4. **Maps** the block ID to a color from the built-in palette
5. **Applies shading** — blocks at higher elevations are slightly brighter, lower ones darker (unless `--no-shade`)
6. **Writes** a PNG file where 1 pixel = 1 block

## Compatibility

- ✅ Minecraft Java Edition **1.12** and earlier (block ID-based format)
- ❌ Minecraft 1.13+ (uses string-based block states — not supported by this version)

## Customizing the Palette

The color palette is defined in the `BLOCK_COLORS` dictionary inside the script. To add or change a block color:

```python
BLOCK_COLORS[<block_id>] = (R, G, B)
```

You can find block IDs in the [Minecraft Wiki](https://minecraft.wiki/w/Java_Edition_data_values/Pre-flattening) (pre-flattening values for 1.12).

## License

[MIT](LICENSE)
