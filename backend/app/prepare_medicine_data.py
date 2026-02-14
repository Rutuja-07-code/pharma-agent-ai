#data created
#auto edited
#needs editing

import pandas as pd
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"
INPUT_FILE = DATA_DIR / "products-export.xlsx"
OUTPUT_FILE = DATA_DIR / "medicine_master.csv"

# Load your dataset
df = pd.read_excel(INPUT_FILE)

# Normalize column names for safer matching
df.columns = (
    df.columns.astype(str)
    .str.strip()
    .str.lower()
    .str.replace(r"\s+", " ", regex=True)
)

# Rename for simplicity
df = df.rename(columns={"product name": "medicine_name", "medicine name": "medicine_name"})

# Keep only useful column
df = df[["medicine_name"]]

# Add dummy stock levels (random)
df["stock"] = [random.randint(10, 100) for _ in range(len(df))]

# Add dummy prescription flags
df["prescription_required"] = [
    random.choice(["Yes", "No"]) for _ in range(len(df))
]

# Save cleaned file
df.to_csv(OUTPUT_FILE, index=False)

print("✅ Medicine Master Data Ready!")
print(df.head())
