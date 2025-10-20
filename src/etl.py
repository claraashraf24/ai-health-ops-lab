import pandas as pd
from pathlib import Path
import csv

file_path = Path("data/emergency_service.csv")

# Try to sniff the delimiter automatically
with open(file_path, "r", encoding="latin1") as f:
    sample = f.read(2048)
    dialect = csv.Sniffer().sniff(sample)
    delimiter = dialect.delimiter

print(f"Detected delimiter: {repr(delimiter)}")

# Now read using that delimiter
df = pd.read_csv(file_path, encoding="latin1", delimiter=delimiter, on_bad_lines="skip")

print("Shape:", df.shape)
print("Columns:", list(df.columns)[:10])
print(df.head())
