#!/usr/bin/env python3
"""
Minecraft World Map Generator for version 1.12

Generates PNG maps from Minecraft world save files.
Supports Overworld (surface mode) and Nether (slice mode).

Usage:
  python minecraft_map.py /path/to/world --out map.png                     # Overworld surface
  python minecraft_map.py /path/to/world --out map.png --y 64              # Overworld slice at Y=64
  python minecraft_map.py /path/to/world --out nether.png --nether         # Nether slice at Y=32
  python minecraft_map.py /path/to/world --out nether.png --nether --y 50  # Nether slice at Y=50

Requirements:
  pip install nbt Pillow
"""

import argparse
import os
import sys
import struct
import zlib
import math
from io import BytesIO

try:
    from nbt.nbt import NBTFile
except ImportError:
    sys.stderr.write("Error: nbt library not found. Install with: pip install nbt\n")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    sys.stderr.write("Error: Pillow not found. Install with: pip install Pillow\n")
    sys.exit(1)


# ============================================================================
# Color palettes
# ============================================================================

# Dye colors by data value (for wool, stained glass, carpet)
DYE_COLORS = {
    0: (230, 230, 230),   1: (235, 160, 55),    2: (195, 75, 180),
    3: (100, 160, 230),   4: (240, 220, 60),     5: (120, 200, 80),
    6: (240, 160, 180),   7: (70, 70, 70),       8: (160, 160, 160),
    9: (70, 160, 160),    10: (130, 60, 180),   11: (60, 70, 180),
    12: (100, 70, 40),    13: (70, 130, 50),     14: (200, 50, 50),
    15: (30, 30, 30),
}

# Terracotta colors (more muted than dye colors)
TERRACOTTA_COLORS = {
    0: (210, 200, 190),   1: (160, 90, 40),     2: (140, 60, 140),
    3: (70, 110, 170),    4: (190, 170, 50),     5: (80, 150, 60),
    6: (200, 120, 140),   7: (55, 55, 55),       8: (120, 120, 120),
    9: (50, 120, 120),   10: (90, 40, 130),    11: (40, 50, 130),
    12: (70, 50, 30),    13: (50, 90, 40),      14: (140, 35, 35),
    15: (20, 20, 20),
}

# Main block palette: block_id -> (R, G, B) or None for transparent/special
BLOCK_COLORS = {
    0: None,               # Air
    1: (128, 128, 128),    # Stone
    2: (96, 160, 64),      # Grass block
    3: (134, 96, 67),      # Dirt
    4: (120, 120, 120),    # Cobblestone
    5: (160, 130, 90),     # Wood planks
    6: (100, 140, 50),     # Sapling
    7: (60, 60, 60),       # Bedrock
    8: (64, 96, 200),      # Water (flowing)
    9: (64, 96, 200),      # Water (still)
    10: (220, 100, 20),    # Lava (flowing)
    11: (220, 100, 20),    # Lava (still)
    12: (220, 210, 160),   # Sand
    13: (140, 130, 120),   # Gravel
    14: (200, 160, 60),    # Gold ore
    15: (180, 160, 150),   # Iron ore
    16: (60, 60, 60),      # Coal ore
    17: (100, 70, 40),     # Log
    18: (60, 110, 40),     # Leaves
    19: (200, 220, 60),    # Sponge
    20: (200, 220, 230),   # Glass
    21: (60, 40, 120),     # Lapis ore
    22: (40, 60, 150),     # Lapis block
    23: (130, 120, 110),   # Dispenser
    24: (220, 210, 160),   # Sandstone
    25: (140, 100, 60),    # Note block
    29: (130, 120, 110),   # Sticky piston
    30: (200, 200, 160),   # Cobweb
    31: (110, 150, 70),    # Tall grass
    32: (110, 140, 60),    # Dead bush
    33: (130, 120, 110),   # Piston
    34: (130, 120, 110),   # Piston head
    35: None,              # Wool (DYE_COLORS by data)
    37: (220, 220, 60),    # Dandelion
    38: (200, 60, 60),     # Poppy
    39: (120, 100, 80),    # Brown mushroom
    40: (200, 80, 80),     # Red mushroom
    41: (230, 200, 60),    # Block of gold
    42: (220, 220, 230),   # Block of iron
    43: (150, 140, 130),   # Double slab
    44: (150, 140, 130),   # Slab
    45: (150, 75, 60),     # Bricks
    46: (180, 60, 50),     # TNT
    47: (180, 160, 80),    # Bookshelf
    48: (70, 110, 90),     # Mossy cobblestone
    49: (40, 20, 50),      # Obsidian
    50: (220, 200, 100),   # Torch
    52: (40, 60, 120),     # Mob spawner
    53: (140, 100, 60),    # Oak stairs
    54: (140, 100, 60),    # Chest
    56: (60, 200, 180),    # Diamond ore
    57: (100, 220, 200),   # Block of diamond
    58: (160, 130, 90),    # Crafting table
    59: (180, 200, 80),    # Wheat
    60: (80, 60, 40),       # Farmland
    61: (130, 120, 110),   # Furnace
    62: (130, 120, 110),   # Furnace (lit)
    65: (100, 80, 50),     # Ladder
    66: (100, 80, 50),     # Rail
    67: (120, 120, 120),   # Stone stairs
    68: (160, 130, 90),    # Sign (wall)
    69: (100, 80, 50),     # Lever
    70: (120, 120, 120),   # Stone pressure plate
    71: (200, 200, 210),   # Iron door
    72: (160, 130, 90),    # Wooden door
    73: (180, 40, 40),     # Redstone ore
    74: (180, 40, 40),     # Redstone ore (lit)
    75: (140, 40, 40),     # Redstone torch (off)
    76: (220, 60, 60),     # Redstone torch (on)
    77: (130, 120, 110),   # Stone button
    78: (240, 240, 250),   # Snow (layer)
    79: (180, 220, 240),   # Ice
    80: (240, 240, 250),   # Snow block
    81: (120, 180, 60),   # Cactus
    82: (180, 200, 200),  # Clay
    83: (150, 180, 80),   # Sugar cane
    84: (120, 80, 50),    # Jukebox
    86: (200, 150, 50),   # Pumpkin
    87: (120, 50, 50),    # Netherrack
    88: (90, 70, 50),     # Soul sand
    89: (220, 200, 60),   # Glowstone
    91: (200, 150, 50),   # Jack-o-lantern
    92: (230, 230, 230),  # Cake
    95: None,              # Stained glass (DYE_COLORS, lighter)
    96: (160, 130, 90),   # Wooden trapdoor
    97: (120, 120, 120),  # Stone monster egg
    98: (180, 180, 180),  # Stone bricks
    99: (100, 160, 60),   # Brown huge mushroom
    100: (200, 60, 60),   # Red huge mushroom
    101: (130, 120, 120), # Iron bars
    102: (200, 220, 230), # Glass pane
    103: (120, 180, 60),  # Melon
    106: (60, 130, 40),   # Vines
    107: (140, 100, 60),  # Oak fence gate
    108: (150, 75, 60),   # Brick stairs
    109: (180, 180, 180), # Stone brick stairs
    110: (100, 80, 60),   # Mycelium
    111: (100, 120, 60),  # Lily pad
    112: (70, 40, 40),    # Nether brick
    113: (70, 40, 40),    # Nether brick fence
    114: (70, 40, 40),    # Nether brick stairs
    115: (140, 30, 30),   # Nether wart
    116: (80, 200, 100),  # Enchantment table
    120: (50, 40, 80),    # End portal frame
    121: (200, 200, 200), # End stone
    122: (200, 180, 100), # Dragon egg
    123: (200, 150, 50),  # Redstone lamp (off)
    124: (220, 180, 80),  # Redstone lamp (on)
    126: (160, 130, 90),  # Wood slab (double)
    127: (140, 100, 60),  # Cocoa
    128: (220, 210, 160), # Sandstone stairs
    129: (140, 110, 70),  # Emerald ore
    130: (50, 90, 50),    # Ender chest
    133: (60, 200, 100),  # Block of emerald
    134: (100, 70, 40),   # Spruce stairs
    135: (200, 180, 140), # Birch stairs
    136: (100, 70, 40),   # Jungle stairs
    137: (180, 140, 70),  # Command block
    138: (200, 200, 220), # Beacon
    139: (120, 120, 120), # Cobblestone wall
    140: (70, 110, 90),   # Mossy cobblestone wall
    141: (160, 110, 70),  # Flower pot
    142: (200, 150, 50),  # Carrots
    143: (180, 200, 80),  # Potatoes
    145: (120, 110, 110), # Anvil
    146: (140, 100, 60),  # Trapped chest
    147: (200, 200, 200), # Light weighted pressure plate
    148: (200, 200, 200), # Heavy weighted pressure plate
    151: (180, 140, 70),  # Daylight sensor
    152: (140, 40, 40),   # Block of redstone
    153: (200, 190, 180), # Nether quartz ore
    154: (130, 120, 110), # Hopper
    155: (220, 215, 205), # Block of quartz
    156: (220, 215, 205), # Quartz stairs
    157: (100, 80, 50),   # Activator rail
    158: (130, 120, 110), # Dropper
    159: None,             # Stained clay (TERRACOTTA_COLORS by data)
    160: None,             # Stained glass pane (DYE_COLORS, lighter)
    161: (60, 110, 40),   # Leaves 2 (acacia/dark oak)
    162: (100, 70, 40),   # Acacia/dark oak log
    163: (160, 80, 50),   # Acacia stairs
    164: (100, 70, 40),   # Dark oak stairs
    165: (180, 140, 70),  # Slime block
    166: (220, 220, 230), # Barrier
    167: (140, 100, 60),  # Iron trapdoor
    168: (120, 160, 170), # Prismarine
    169: (100, 200, 180), # Sea lantern
    170: (200, 150, 80),  # Hay block
    171: None,             # Carpet (DYE_COLORS by data)
    172: (120, 100, 80),  # Hardened clay
    173: (40, 40, 40),    # Block of coal
    174: (180, 220, 240), # Packed ice
    175: (110, 150, 70),  # Double plant
    179: (200, 190, 180), # Red sandstone
    180: (200, 190, 180), # Red sandstone stairs
    181: (200, 190, 180), # Red sandstone slab (double)
    182: (200, 190, 180), # Red sandstone slab
    198: (130, 120, 110), # End rod
    199: (200, 200, 200), # Chorus plant
    200: (180, 140, 200), # Chorus flower
    201: (210, 200, 190), # Purpur block
    202: (210, 200, 190), # Purpur pillar
    203: (210, 200, 190), # Purpur stairs
    205: (210, 200, 190), # Purpur slab (double)
    206: (210, 200, 190), # Purpur slab
    207: (220, 220, 220), # End stone bricks
    212: (180, 220, 240), # Frosted ice
}

# Blocks treated as transparent in surface mode (skipped when searching for surface)
TRANSPARENT_BLOCKS = {
    0, 6, 26, 27, 28, 30, 31, 32, 34, 37, 38, 39, 40, 50, 55, 59,
    63, 64, 65, 66, 68, 69, 70, 71, 72, 75, 76, 77, 78, 83, 92,
    93, 94, 96, 101, 102, 104, 105, 106, 107, 111, 115, 119, 127,
    131, 132, 140, 141, 142, 143, 144, 145, 147, 148, 149, 150,
    151, 157, 167, 171, 175, 183, 184, 185, 186, 187, 198, 199, 200, 209,
}

# Log data values -> color (for block ID 17)
LOG_COLORS = {
    0: (100, 70, 40),   # Oak
    1: (100, 70, 40),
    2: (100, 70, 40),
    3: (100, 70, 40),
    4: (70, 55, 35),    # Spruce
    5: (70, 55, 35),
    6: (70, 55, 35),
    7: (70, 55, 35),
    8: (200, 180, 140), # Birch
    9: (200, 180, 140),
    10: (200, 180, 140),
    11: (200, 180, 140),
    12: (100, 80, 50),  # Jungle
    13: (100, 80, 50),
    14: (100, 80, 50),
    15: (100, 80, 50),
}

# Leaves data values -> color (for block ID 18)
LEAVES_COLORS = {
    0: (60, 110, 40),   # Oak
    1: (60, 110, 40),
    2: (60, 110, 40),
    3: (60, 110, 40),
    4: (50, 80, 50),    # Spruce (darker)
    5: (50, 80, 50),
    6: (50, 80, 50),
    7: (50, 80, 50),
    8: (120, 150, 80),  # Birch
    9: (120, 150, 80),
    10: (120, 150, 80),
    11: (120, 150, 80),
    12: (40, 100, 40),  # Jungle
    13: (40, 100, 40),
    14: (40, 100, 40),
    15: (40, 100, 40),
}

# Wood planks data values -> color (for block ID 5)
PLANKS_COLORS = {
    0: (160, 130, 90),  # Oak
    1: (100, 70, 40),   # Spruce
    2: (200, 180, 140), # Birch
    3: (100, 80, 50),   # Jungle
    4: (160, 80, 50),   # Acacia
    5: (70, 50, 35),    # Dark Oak
}

# Leaves 2 data values -> color (for block ID 161)
LEAVES2_COLORS = {
    0: (160, 80, 50),   # Acacia
    1: (160, 80, 50),
    2: (160, 80, 50),
    3: (160, 80, 50),
    4: (70, 50, 35),    # Dark Oak
    5: (70, 50, 35),
    6: (70, 50, 35),
    7: (70, 50, 35),
}

# Log 2 data values -> color (for block ID 162)
LOG2_COLORS = {
    0: (160, 80, 50),   # Acacia
    1: (160, 80, 50),
    2: (160, 80, 50),
    3: (160, 80, 50),
    4: (70, 50, 35),    # Dark Oak
    5: (70, 50, 35),
    6: (70, 50, 35),
    7: (70, 50, 35),
}


# ============================================================================
# Color resolution
# ============================================================================

def get_block_color(block_id, data_value=0):
    """Resolve block color from block_id and data_value.
    Returns (R, G, B) tuple, or None for transparent/special blocks.
    """
    if block_id == 0:
        return None  # Air

    # Blocks with data-dependent colors
    if block_id == 17:  # Log
        return LOG_COLORS.get(data_value, (100, 70, 40))
    if block_id == 18:  # Leaves
        return LEAVES_COLORS.get(data_value, (60, 110, 40))
    if block_id == 5:   # Wood planks
        return PLANKS_COLORS.get(data_value, (160, 130, 90))
    if block_id == 161:  # Leaves 2
        return LEAVES2_COLORS.get(data_value, (60, 110, 40))
    if block_id == 162:  # Log 2
        return LOG2_COLORS.get(data_value, (160, 80, 50))
    if block_id == 35:   # Wool
        return DYE_COLORS.get(data_value, (230, 230, 230))
    if block_id == 95:   # Stained glass
        c = DYE_COLORS.get(data_value, (200, 220, 230))
        return (min(255, c[0] + 20), min(255, c[1] + 20), min(255, c[2] + 20))
    if block_id == 160:  # Stained glass pane
        c = DYE_COLORS.get(data_value, (200, 220, 230))
        return (min(255, c[0] + 20), min(255, c[1] + 20), min(255, c[2] + 20))
    if block_id == 159:  # Stained clay
        return TERRACOTTA_COLORS.get(data_value, (120, 100, 80))
    if block_id == 171:  # Carpet
        return DYE_COLORS.get(data_value, (230, 230, 230))
    if block_id == 168:  # Prismarine
        if data_value == 0: return (120, 160, 170)
        elif data_value == 1: return (90, 130, 140)
        elif data_value == 2: return (150, 190, 200)
        return (120, 160, 170)
    if block_id == 98:   # Stone bricks
        if data_value == 1: return (140, 140, 130)  # Mossy
        elif data_value == 2: return (160, 160, 150)  # Cracked
        return (180, 180, 180)
    if block_id == 24:   # Sandstone
        if data_value == 1: return (200, 190, 160)  # Chiseled
        elif data_value == 2: return (210, 200, 170)  # Smooth
        return (220, 210, 160)
    if block_id == 43:   # Double slab
        # Check data value for slab type
        slab_colors = {0: (128, 128, 128), 1: (160, 130, 90), 3: (150, 140, 130),
                       4: (200, 200, 200), 5: (200, 190, 180), 6: (210, 200, 190),
                       7: (120, 100, 80), 8: (120, 160, 170), 9: (90, 130, 140)}
        return slab_colors.get(data_value, (150, 140, 130))
    if block_id == 44:   # Slab
        slab_colors = {0: (128, 128, 128), 1: (160, 130, 90), 3: (150, 140, 130),
                       4: (200, 200, 200), 5: (200, 190, 180), 6: (210, 200, 190),
                       7: (120, 100, 80), 8: (120, 160, 170), 9: (90, 130, 140)}
        return slab_colors.get(data_value, (150, 140, 130))

    # Simple lookup
    color = BLOCK_COLORS.get(block_id)
    if color is not None:
        return color

    # Unknown block — return magenta for visibility
    return (170, 0, 170)


def is_transparent(block_id):
    """Check if a block should be skipped in surface mode."""
    return block_id in TRANSPARENT_BLOCKS


# ============================================================================
# Region file (.mca) reading
# ============================================================================

def read_region_file(filepath):
    """Read all chunks from a .mca region file.
    Returns dict: {(chunk_x, chunk_z) -> NBTFile}
    """
    chunks = {}
    with open(filepath, 'rb') as f:
        locations = f.read(4096)
        f.read(4096)  # timestamps (skip)

        for i in range(1024):
            offset = (locations[i * 4] << 16) | (locations[i * 4 + 1] << 8) | locations[i * 4 + 2]
            sector_count = locations[i * 4 + 3]

            if offset == 0 and sector_count == 0:
                continue

            chunk_x = i % 32
            chunk_z = i // 32

            f.seek(offset * 4096)
            length_data = f.read(4)
            if len(length_data) < 4:
                continue
            length = struct.unpack('>I', length_data)[0]
            if length < 1:
                continue

            compression_type = f.read(1)[0]
            raw_data = f.read(length - 1)

            try:
                if compression_type == 2:  # zlib
                    data = zlib.decompress(raw_data)
                elif compression_type == 1:  # gzip
                    import gzip
                    data = gzip.decompress(raw_data)
                else:
                    continue

                nbt = NBTFile(buffer=BytesIO(data))
                chunks[(chunk_x, chunk_z)] = nbt
            except Exception as e:
                sys.stderr.write(f"  Warning: Failed to read chunk ({chunk_x}, {chunk_z}) in {filepath}: {e}\n")

    return chunks


# ============================================================================
# Block data extraction
# ============================================================================

def get_section_map(chunk_nbt):
    """Build a dict {section_Y -> section_tag} from chunk NBT."""
    sections = {}
    if 'Level' not in chunk_nbt:
        return sections
    level = chunk_nbt['Level']
    if 'Sections' not in level:
        return sections
    for section in level['Sections']:
        y_val = section['Y'].value
        sections[y_val] = section
    return sections


def get_block_at(sections, x, y, z):
    """Get block ID and data value at local coords (x, y, z) within a chunk.
    x: 0-15, y: 0-255, z: 0-15
    Returns (block_id, data_value)
    """
    section_index = y >> 4
    local_y = y & 0xF

    if section_index not in sections:
        return 0, 0

    section = sections[section_index]
    if 'Blocks' not in section:
        return 0, 0

    blocks = section['Blocks'].value
    # Index formula: (y * 16 + z) * 16 + x
    index = (local_y * 16 + z) * 16 + x

    if index >= len(blocks):
        return 0, 0

    block_id = blocks[index] & 0xFF

    # Extended block IDs via Add array
    if 'Add' in section:
        add_data = section['Add'].value
        if index // 2 < len(add_data):
            add_nibble = (add_data[index >> 1] >> ((index & 1) << 2)) & 0xF
            block_id = (add_nibble << 8) | block_id

    # Data value
    data_value = 0
    if 'Data' in section:
        data_data = section['Data'].value
        if index >> 1 < len(data_data):
            data_value = (data_data[index >> 1] >> ((index & 1) << 2)) & 0xF

    return block_id, data_value


# ============================================================================
# Map generation
# ============================================================================

def generate_map(world_path, output_path, fixed_y=None, nether=False, shade=True):
    """Generate a PNG map from a Minecraft world."""

    # Determine region directory
    if nether:
        region_dir = os.path.join(world_path, 'DIM-1', 'region')
        if fixed_y is None:
            fixed_y = 32  # Default Nether slice height
    else:
        region_dir = os.path.join(world_path, 'region')

    if not os.path.isdir(region_dir):
        sys.stderr.write(f"Error: Region directory not found: {region_dir}\n")
        if nether:
            sys.stderr.write("  (Make sure the world has a Nether dimension — try visiting it in-game first)\n")
        sys.exit(1)

    # Find all .mca files
    mca_files = [f for f in os.listdir(region_dir) if f.endswith('.mca')]
    if not mca_files:
        sys.stderr.write(f"Error: No .mca files found in {region_dir}\n")
        sys.exit(1)

    # Parse region file coordinates from filenames: r.X.Z.mca
    region_coords = []
    for filename in mca_files:
        parts = filename.split('.')
        if len(parts) >= 4 and parts[0] == 'r':
            try:
                rx, rz = int(parts[1]), int(parts[2])
                region_coords.append((rx, rz, os.path.join(region_dir, filename)))
            except ValueError:
                continue

    if not region_coords:
        sys.stderr.write("Error: Could not parse region file coordinates\n")
        sys.exit(1)

    min_rx = min(rc[0] for rc in region_coords)
    max_rx = max(rc[0] for rc in region_coords)
    min_rz = min(rc[1] for rc in region_coords)
    max_rz = max(rc[1] for rc in region_coords)

    # World bounds in blocks
    min_block_x = min_rx * 512
    min_block_z = min_rz * 512
    width_blocks = (max_rx - min_rx + 1) * 512
    height_blocks = (max_rz - min_rz + 1) * 512

    sys.stderr.write(f"World bounds: {min_block_x},{min_block_z} to {min_block_x + width_blocks},{min_block_z + height_blocks}\n")
    sys.stderr.write(f"Image size: {width_blocks}x{height_blocks} pixels\n")
    sys.stderr.write(f"Mode: {'slice Y=' + str(fixed_y) if fixed_y is not None else 'surface'} | Dimension: {'Nether' if nether else 'Overworld'}\n")

    # Create image
    img = Image.new('RGB', (width_blocks, height_blocks), (0, 0, 0))
    pixels = img.load()

    total_regions = len(region_coords)
    regions_done = 0

    for rx, rz, filepath in region_coords:
        regions_done += 1
        sys.stderr.write(f"\rProcessing region {regions_done}/{total_regions}: r.{rx}.{rz}.mca    ")
        sys.stderr.flush()

        chunks = read_region_file(filepath)
        if not chunks:
            continue

        for (chunk_x, chunk_z), chunk_nbt in chunks.items():
            sections = get_section_map(chunk_nbt)
            if not sections:
                continue

            # World position of this chunk
            world_chunk_x = rx * 32 + chunk_x
            world_chunk_z = rz * 32 + chunk_z

            # Pixel offset for this chunk
            px_offset = (world_chunk_x * 16 - min_block_x)
            pz_offset = (world_chunk_z * 16 - min_block_z)

            if px_offset < 0 or pz_offset < 0:
                continue
            if px_offset + 16 > width_blocks or pz_offset + 16 > height_blocks:
                continue

            for x in range(16):
                for z in range(16):
                    color = None
                    surface_y = 0

                    if fixed_y is not None:
                        # Slice mode: get block at fixed Y
                        block_id, data_val = get_block_at(sections, x, fixed_y, z)
                        color = get_block_color(block_id, data_val)
                        surface_y = fixed_y
                        if color is None:
                            color = (10, 10, 10)  # Dark for air in slice mode
                    else:
                        # Surface mode: find topmost non-transparent block
                        for y in range(255, -1, -1):
                            block_id, data_val = get_block_at(sections, x, y, z)
                            if block_id != 0 and not is_transparent(block_id):
                                color = get_block_color(block_id, data_val)
                                surface_y = y
                                break
                        if color is None:
                            # Check if there's water at least
                            for y in range(255, -1, -1):
                                block_id, data_val = get_block_at(sections, x, y, z)
                                if block_id == 8 or block_id == 9:
                                    color = (64, 96, 200)
                                    surface_y = y
                                    break
                        if color is None:
                            color = (10, 10, 10)
                            surface_y = 0

                    # Apply height shading (surface mode only, not for nether/slice)
                    if shade and fixed_y is None and color is not None:
                        # Simple shading based on absolute height
                        # Normalize height to 0-255 range
                        height_factor = surface_y / 255.0
                        # Brighten high areas, darken low areas
                        shade_mult = 0.7 + height_factor * 0.6
                        shade_mult = max(0.5, min(1.3, shade_mult))
                        r = min(255, int(color[0] * shade_mult))
                        g = min(255, int(color[1] * shade_mult))
                        b = min(255, int(color[2] * shade_mult))
                        color = (r, g, b)

                    px = px_offset + x
                    pz = pz_offset + z
                    if 0 <= px < width_blocks and 0 <= pz < height_blocks:
                        pixels[px, pz] = color

    sys.stderr.write("\nDone!\n")

    # Save image
    img.save(output_path, 'PNG')
    sys.stderr.write(f"Map saved to: {output_path}\n")
    img_size = os.path.getsize(output_path)
    if img_size > 1024 * 1024:
        sys.stderr.write(f"File size: {img_size / 1024 / 1024:.1f} MB\n")
    else:
        sys.stderr.write(f"File size: {img_size / 1024:.0f} KB\n")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Generate PNG map from Minecraft 1.12 world save',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python minecraft_map.py /path/to/world --out map.png                     # Overworld surface
  python minecraft_map.py /path/to/world --out map.png --y 64              # Overworld slice at Y=64
  python minecraft_map.py /path/to/world --out nether.png --nether         # Nether slice at Y=32
  python minecraft_map.py /path/to/world --out nether.png --nether --y 50  # Nether slice at Y=50
        """
    )
    parser.add_argument('world', help='Path to Minecraft world folder (contains level.dat)')
    parser.add_argument('--out', default='map.png', help='Output PNG file (default: map.png)')
    parser.add_argument('--y', type=int, default=None,
                        help='Fixed Y height for slice mode (e.g. 64 for overworld, 32 for nether)')
    parser.add_argument('--nether', action='store_true',
                        help='Map the Nether dimension (default slice Y=32)')
    parser.add_argument('--no-shade', action='store_true',
                        help='Disable height-based shading')

    args = parser.parse_args()

    if not os.path.isdir(args.world):
        sys.stderr.write(f"Error: World directory not found: {args.world}\n")
        sys.exit(1)

    generate_map(
        world_path=args.world,
        output_path=args.out,
        fixed_y=args.y,
        nether=args.nether,
        shade=not args.no_shade,
    )


if __name__ == '__main__':
    main()
