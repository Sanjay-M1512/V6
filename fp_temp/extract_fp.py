from pathlib import Path
from PIL import Image
import wsq


INPUT_FILE = Path(__file__).parent / "a001.02_07.firpiv"
OUTPUT_DIR = Path(__file__).parent / "output"

OUTPUT_DIR.mkdir(exist_ok=True)


def read_uint(data, start, length):
    return int.from_bytes(data[start:start + length], "big")


with open(INPUT_FILE, "rb") as f:
    data = f.read()


# Find FIR header
fir_pos = data.find(b"FIR\x00")

if fir_pos == -1:
    raise ValueError("FIR header not found. This may not be a FIRPIV file.")


print("FIR header found at:", fir_pos)


# ---------------------------------------------------------
# FIR general header
# ---------------------------------------------------------

# General header is 36 bytes for this format
header_start = fir_pos

version = data[fir_pos + 4:fir_pos + 8].rstrip(b"\x00").decode()

record_length = read_uint(data, fir_pos + 8, 6)

number_of_fingerprints = data[fir_pos + 22]

compression = data[fir_pos + 33]

print("Version:", version)
print("Record length:", record_length)
print("Number of fingerprints:", number_of_fingerprints)
print("Compression algorithm:", compression)

if compression != 2:
    print("Warning: expected WSQ compression (2).")


# ---------------------------------------------------------
# Finger records start after 36-byte general header
# ---------------------------------------------------------

position = fir_pos + 36


for i in range(number_of_fingerprints):

    # 14-byte finger record header
    block_length = read_uint(data, position, 4)

    finger_position = data[position + 4]
    view_number = data[position + 5]
    quality = data[position + 7]
    impression_type = data[position + 8]

    width = read_uint(data, position + 9, 2)
    height = read_uint(data, position + 11, 2)

    image_start = position + 14
    image_end = position + block_length

    wsq_data = data[image_start:image_end]

    print()
    print("------------------------------")
    print("Fingerprint:", i + 1)
    print("Finger position:", finger_position)
    print("View:", view_number)
    print("Quality:", quality)
    print("Width:", width)
    print("Height:", height)
    print("WSQ bytes:", len(wsq_data))
    print("WSQ header:", wsq_data[:4].hex(" "))

    # Save the extracted WSQ file
    wsq_file = OUTPUT_DIR / f"fingerprint_{i + 1}.wsq"

    with open(wsq_file, "wb") as f:
        f.write(wsq_data)

    # Decode WSQ using Pillow + wsq
    image = Image.open(wsq_file)

    # Convert to PNG
    png_file = OUTPUT_DIR / f"fingerprint_{i + 1}.png"

    image.save(png_file)

    print("WSQ saved:", wsq_file)
    print("PNG saved:", png_file)

    position = image_end


print()
print("Done!")
print("Open the PNG files inside the 'output' folder.")