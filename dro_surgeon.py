import sys
import struct
import signal

# Handle broken pipes (e.g., when piping to head)
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

def get_channel_from_reg(bank, reg):
    """
    Returns the OPL3 channel number (0-17) for a given bank and register.
    Returns -1 if the register is not channel-specific.
    """
    base_ch = 0 if bank == 0 else 9
    
    # 0xA0-0xA8: F-Number Low
    # 0xB0-0xB8: KeyOn / Block / F-Number High
    # 0xC0-0xC8: Feedback / Connection
    if (0xA0 <= reg <= 0xA8) or (0xB0 <= reg <= 0xB8) or (0xC0 <= reg <= 0xC8):
        return base_ch + (reg & 0x0F)
        
    # Operator registers (offset by 0, 1, ... for each operator)
    # 0x20-0x35: TVSKM
    # 0x40-0x55: KSL/Level
    # 0x60-0x75: Attack/Decay
    # 0x80-0x95: Sustain/Release
    # 0xE0-0xF5: Waveform Select
    if (0x20 <= reg <= 0x35) or (0x40 <= reg <= 0x55) or (0x60 <= reg <= 0x75) or \
       (0x80 <= reg <= 0x95) or (0xE0 <= reg <= 0xF5):
        # The offset within the range determines the operator, which maps to a channel.
        # Offsets: 00,01,02,03,04,05,08,09,0A,0B,0C,0D,10,11,12,13,14,15
        # Maps to Ch: 0, 1, 2, 0, 1, 2, 3, 4, 5, 3, 4, 5, 6, 7, 8, 6, 7, 8
        # Simple lookup for the offset 0x00-0x15:
        offset = reg % 0x20 # Get low 5 bits effectively
        if offset > 0x15: return -1 # Should not happen based on ranges above
        
        # Channel map for operator offsets
        op_ch_map = [0, 1, 2, 0, 1, 2, -1, -1, 3, 4, 5, 3, 4, 5, -1, -1, 6, 7, 8, 6, 7, 8]
        if offset < len(op_ch_map):
            ch_offset = op_ch_map[offset]
            if ch_offset != -1:
                return base_ch + ch_offset
                
    return -1

def remove_channel(filename, target_channel, output_filename):
    with open(filename, 'rb') as f:
        data = f.read()

    if data[0:8] != b'DBRAWOPL':
        print("Error: Not a valid DRO file")
        return

    ver_major = struct.unpack('<H', data[8:10])[0]
    if ver_major != 2:
        print("Error: Only DRO v2.0 is supported")
        return

    short_delay_code = data[23]
    long_delay_code = data[24]
    codemap_len = data[25]
    codemap_start = 26
    
    codemap = data[codemap_start : codemap_start + codemap_len]
    
    # Start writing output
    out_data = bytearray()
    
    # 1. Copy Header and Codemap verbatim
    stream_start = codemap_start + codemap_len
    out_data.extend(data[:stream_start])
    
    # 2. Process Stream
    i = stream_start
    dropped_commands = 0
    
    while i < len(data):
        code = data[i]
        i += 1
        
        # Delay Codes - Copy unchanged
        if code == short_delay_code or code == long_delay_code:
            val = data[i]
            i += 1
            out_data.append(code)
            out_data.append(val)
            continue
            
        # Register Write
        val = data[i]
        i += 1
        
        bank = (code >> 7) & 1
        idx = code & 0x7F
        
        if idx >= len(codemap):
            # Invalid index, just copy it to be safe
            out_data.append(code)
            out_data.append(val)
            continue
            
        reg = codemap[idx]
        ch = get_channel_from_reg(bank, reg)
        
        if ch == target_channel:
            dropped_commands += 1
            # Do NOT append to out_data
        else:
            out_data.append(code)
            out_data.append(val)

    with open(output_filename, 'wb') as f_out:
        f_out.write(out_data)
        
    print(f"Removed Channel {target_channel}.")
    print(f"Dropped {dropped_commands} commands.")
    print(f"Saved to {output_filename}")

def isolate_channel(filename, target_channel, output_filename):
    with open(filename, 'rb') as f:
        data = f.read()

    if data[0:8] != b'DBRAWOPL':
        print("Error: Not a valid DRO file")
        return

    ver_major = struct.unpack('<H', data[8:10])[0]
    if ver_major != 2:
        print("Error: Only DRO v2.0 is supported")
        return

    short_delay_code = data[23]
    long_delay_code = data[24]
    codemap_len = data[25]
    codemap_start = 26
    
    codemap = data[codemap_start : codemap_start + codemap_len]
    
    # Start writing output
    out_data = bytearray()
    
    # 1. Copy Header and Codemap verbatim
    stream_start = codemap_start + codemap_len
    out_data.extend(data[:stream_start])
    
    # 2. Process Stream
    i = stream_start
    dropped_commands = 0
    
    while i < len(data):
        code = data[i]
        i += 1
        
        # Delay Codes - Copy unchanged
        if code == short_delay_code or code == long_delay_code:
            val = data[i]
            i += 1
            out_data.append(code)
            out_data.append(val)
            continue
            
        # Register Write
        val = data[i]
        i += 1
        
        bank = (code >> 7) & 1
        idx = code & 0x7F
        
        if idx >= len(codemap):
            # Invalid index, just copy it
            out_data.append(code)
            out_data.append(val)
            continue
            
        reg = codemap[idx]
        ch = get_channel_from_reg(bank, reg)
        
        # ALWAYS keep global/rhythm control (0xBD)
        if reg == 0xBD:
             out_data.append(code)
             out_data.append(val)
             continue
        
        if ch == target_channel or ch == -1: # Keep target AND global settings (-1)
            out_data.append(code)
            out_data.append(val)
        else:
            dropped_commands += 1
            # Skip

    with open(output_filename, 'wb') as f_out:
        f_out.write(out_data)
        
    print(f"Isolated Channel {target_channel}.")
    print(f"Dropped {dropped_commands} other commands.")
    print(f"Saved to {output_filename}")

def dump_dro(filename):
    with open(filename, 'rb') as f:
        data = f.read()

    if data[0:8] != b'DBRAWOPL':
        print("Error: Not a valid DRO file (missing magic 'DBRAWOPL')")
        return

    ver_major = struct.unpack('<H', data[8:10])[0]
    ver_minor = struct.unpack('<H', data[10:12])[0]
    
    if ver_major != 2:
        print(f"Error: This script only supports DRO v2.0 (Found v{ver_major}.{ver_minor})")
        return

    # DRO v2 Header Offsets
    # 12-15: Length Pairs
    # 16-19: Length MS
    # 20: Hardware
    # 21: Format
    # 22: Compression
    # 23: Short Delay Code
    # 24: Long Delay Code
    # 25: Codemap Length
    
    short_delay_code = data[23]
    long_delay_code = data[24]
    codemap_len = data[25]
    
    print(f"Header Info: ShortDelay=0x{short_delay_code:02X}, LongDelay=0x{long_delay_code:02X}, CodemapLen={codemap_len}")
    
    codemap_start = 26
    codemap = data[codemap_start : codemap_start + codemap_len]
    
    # Stream starts immediately after the codemap
    i = codemap_start + codemap_len
    time_accum = 0
    
    print(f"{'OFFSET(h)':<10} | {'TIME(ms)':<8} | {'BNK':<3} | {'REG':<4} | {'VAL':<4} | {'DESC'}")
    print("-" * 70)

    while i < len(data):
        offset = i
        code = data[i]
        i += 1
        
        # Check for Delay Codes
        if code == short_delay_code:
            if i >= len(data): break
            val = data[i]
            i += 1
            delay = val + 1
            time_accum += delay
            continue
            
        elif code == long_delay_code:
            if i >= len(data): break
            val = data[i]
            i += 1
            delay = (val + 1) * 256
            time_accum += delay
            continue
        
        # If not a delay, it's a register write
        # In DRO v2:
        # Bank = (Code >> 7) & 1  (0 or 1)
        # Index = Code & 0x7F     (0-127)
        # We look up the actual OPL Register in the Codemap
        
        if i >= len(data): break
        val = data[i] # The value to write to the register
        i += 1
        
        bank = (code >> 7) & 1
        idx = code & 0x7F
        
        if idx >= len(codemap):
            # This shouldn't technically happen in a valid file unless codemap is short
            desc = f"ERROR: Index {idx} out of bounds"
            print(f"{offset:08X}   | {time_accum:<8} | {bank}   | {idx:02X}?  | {val:02X}   | {desc}")
            continue

        reg = codemap[idx]
        
        # Human Readable Description
        desc = ""
        
        # B0-B8: KeyOn / Block / FreqHigh
        if 0xB0 <= reg <= 0xB8:
            ch = reg - 0xB0
            key_on = (val & 0x20) != 0
            block = (val & 0x1C) >> 2
            f_high = val & 0x03
            desc = f"CH {ch} | KeyOn: {key_on} | Blk: {block} | F-Hi: {f_high}"
            if key_on:
                desc += " <--- NOTE START"
        
        # A0-A8: FreqLow
        elif 0xA0 <= reg <= 0xA8:
            ch = reg - 0xA0
            desc = f"CH {ch} | F-Low: {val}"
            
        # C0-C8: Feedback / Connection (Algorithm)
        elif 0xC0 <= reg <= 0xC8:
            ch = reg - 0xC0
            fb = (val & 0x0E) >> 1
            cnt = val & 1
            desc = f"CH {ch} | FB: {fb} | CNT: {cnt}"
            
        # 20-35: Tremolo / Vibrato / Sustain / KSR / Multiplier
        elif 0x20 <= reg <= 0x35:
            op_offset = reg - 0x20
            desc = f"OP-Reg {reg:02X} | TVSKM"

        # 40-55: KSL / Level
        elif 0x40 <= reg <= 0x55:
            desc = f"OP-Reg {reg:02X} | Level: {val & 0x3F}"
            
        # BD: Rhythm
        elif reg == 0xBD:
            desc = "Rhythm Control"

        if desc:
            print(f"{offset:08X}   | {time_accum:<8} | {bank}   | {reg:02X}   | {val:02X}   | {desc}")

def calc_shift(hex_a0, hex_b0, semitones):
    # hex_a0 is the value at register A0-A8 (F-Num Low)
    # hex_b0 is the value at register B0-B8 (KeyOn + Block + F-Num High)
    
    # 1. Parse current state
    f_low = hex_a0
    key_on = (hex_b0 & 0x20)
    block = (hex_b0 & 0x1C) >> 2
    f_high = (hex_b0 & 0x03)
    
    current_f_num = (f_high << 8) | f_low
    
    print(f"Original -> Block: {block}, F-Num: {current_f_num}")
    
    # 2. Calculate Pitch Shift
    # Formula: F_new = F_old * 2^(semitones/12)
    multiplier = 2 ** (semitones / 12.0)
    new_f_num = int(current_f_num * multiplier)
    new_block = block
    
    # 3. Handle Block Overflow/Underflow
    # OPL F-Num must be < 1024. If it goes over, increase octave (Block).
    while new_f_num >= 1024 and new_block < 7:
        new_f_num //= 2
        new_block += 1
    while new_f_num < 512 and new_block > 0: # Normalize
        new_f_num *= 2
        new_block -= 1
        
    print(f"New      -> Block: {new_block}, F-Num: {new_f_num}")
    
    # 4. Re-pack to Hex
    new_f_low = new_f_num & 0xFF
    new_f_high = (new_f_num >> 8) & 0x03
    
    new_b0_val = key_on | (new_block << 2) | new_f_high
    
    print(f"\nREPLACE BYTES IN HEX EDITOR:")
    print(f"Reg A{hex_b0 & 0x0F} (F-Low) : {hex_a0:02X} -> {new_f_low:02X}")
    print(f"Reg B{hex_b0 & 0x0F} (Block) : {hex_b0:02X} -> {new_b0_val:02X}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 dro_surgeon.py dump <file.dro>")
        print("       python3 dro_surgeon.py remove <input.dro> <channel_num> <output.dro>")
        print("       python3 dro_surgeon.py isolate <input.dro> <channel_num> <output.dro>")
        print("       python3 dro_surgeon.py calc <HexA0> <HexB0> <Semitones>")
        sys.exit(1)

    if sys.argv[1] == "dump":
        dump_dro(sys.argv[2])
    elif sys.argv[1] == "remove":
        # python3 dro_surgeon.py remove input.dro 5 output.dro
        if len(sys.argv) < 5:
            print("Error: Missing arguments for remove")
            sys.exit(1)
        remove_channel(sys.argv[2], int(sys.argv[3]), sys.argv[4])
    elif sys.argv[1] == "isolate":
        if len(sys.argv) < 5:
            print("Error: Missing arguments for isolate")
            sys.exit(1)
        isolate_channel(sys.argv[2], int(sys.argv[3]), sys.argv[4])
    elif sys.argv[1] == "calc":
        # Input format: python script.py calc E2 31 -2
        a0 = int(sys.argv[2], 16)
        b0 = int(sys.argv[3], 16)
        semi = float(sys.argv[4])
        calc_shift(a0, b0, semi)