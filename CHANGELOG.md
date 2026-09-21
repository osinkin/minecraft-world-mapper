# Changelog

## [1.1.0] - 2026-09-21

### Added
- Nether world support (`--nether` flag, reads from `DIM-1/region/`)
- Height-slice mode (`--y` option) for cross-section maps at any Y-level
- Nether block palette: netherrack, soul sand, glowstone, nether bricks, quartz ore, magma blocks, lava
- `--no-shade` flag as an alias for `--mode top`
- Dark color for air/empty blocks in slice mode (visible caves and tunnels)
- `.gitignore`, `requirements.txt`, `LICENSE`

### Changed
- Region path resolution now checks `DIM-1/region/` when `--nether` is set
- Default Y-slice for Nether is 32 (bypasses bedrock ceiling)

## [1.0.0] - Initial release

- Overworld surface map with hill-shading
- 60+ block color mappings
- Support for wool, stained clay, and stained glass variants
- Unknown block highlighting (magenta)
- Progress output to console
