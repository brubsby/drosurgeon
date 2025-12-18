# drosurgeon

A toolkit for inspecting and modifying DRO (DOSBox Raw OPL) music files.

## Usage

```bash
# Dump file events to stdout
python3 dro_surgeon.py dump <file.dro>

# Remove a specific channel (0-17)
python3 dro_surgeon.py remove <input.dro> <channel_num> <output.dro>

# Isolate a specific channel (removes all others)
python3 dro_surgeon.py isolate <input.dro> <channel_num> <output.dro>

# Calculate register values for pitch shifting
python3 dro_surgeon.py calc <HexA0> <HexB0> <Semitones>
```

## Channel Mapping
- **Channels 0-8:** OPL3 Bank 0
- **Channels 9-17:** OPL3 Bank 1

## Manual Pitch Shifting (calc)
The `calc` command assists with manual hex editing. If you want to change the pitch of a specific note found via `dump`:
1. Identify the registers for the note (e.g., `A0` value `EE`, `B0` value `26`).
2. Run `calc`:
   ```bash
   python3 dro_surgeon.py calc EE 26 -2  # Lower by 2 semitones
   ```
3. The tool will calculate the new OPL3 register values (F-Number/Block) required for the target pitch.

## Requirements
- Python 3
- (Optional) `droplay` fork (for rendering to WAV): https://github.com/brubsby/droplay
