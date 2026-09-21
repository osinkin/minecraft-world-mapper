# Contributing

Contributions are welcome! Here are some ways you can help:

## Reporting Issues

- Use [GitHub Issues](../../issues) to report bugs or request features
- Include your Minecraft version, Python version, and OS
- Attach a screenshot if applicable

## Adding Block Colors

If you find blocks rendered in magenta (unknown), you can add them to the palette:

1. Find the block ID in the [Minecraft Wiki](https://minecraft.wiki/w/Java_Edition_data_values/Pre-flattening)
2. Add an entry to `BLOCK_COLORS` in `minecraft_map.py`:
   ```python
   BLOCK_COLORS[block_id] = (R, G, B)
   ```
3. Test with your world and submit a pull request

## Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-blocks`
3. Commit your changes: `git commit -m 'Add nether brick fence color'`
4. Push to the branch: `git push origin feature/new-blocks`
5. Open a pull request

## Ideas for Future Work

- Biome-based coloring mode
- Isometric projection
- Coordinate grid overlay
- Web-based viewer
- Minecraft 1.13+ support (block states instead of numeric IDs)
- Multi-threaded region processing
