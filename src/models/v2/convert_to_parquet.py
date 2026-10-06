import pandas as pd
import numpy as np
from pathlib import Path
import os

def main():
    print("Converting V2 features.csv to parquet...")
    
    in_dir = Path('data/processed/v2')
    src_dir = Path('src/models/v2')
    src_dir.mkdir(parents=True, exist_ok=True)
    
    csv_file = in_dir / 'features.csv'
    pq_file = in_dir / 'features.parquet'
    
    if pq_file.exists():
        print(f"{pq_file} already exists. Skipping conversion.")
        return
        
    # Read in chunks to prevent memory blowup and downcast types
    chunk_size = 500_000
    chunks = []
    
    print(f"Reading {csv_file} in chunks...")
    for i, chunk in enumerate(pd.read_csv(csv_file, chunksize=chunk_size)):
        print(f"Processing chunk {i+1}...")
        # Optimize types
        chunk['date'] = pd.to_datetime(chunk['date'])
        
        # Downcast floats to float32
        float_cols = chunk.select_dtypes(include=['float64']).columns
        chunk[float_cols] = chunk[float_cols].astype('float32')
        
        # Downcast ints to int32 (except possibly household_id if it's string)
        int_cols = chunk.select_dtypes(include=['int64']).columns
        chunk[int_cols] = chunk[int_cols].astype('int32')
        
        # Convert categoricals
        cat_cols = ['household_id', 'Acorn', 'Acorn_grouped', 'stdorToU']
        for col in cat_cols:
            if col in chunk.columns:
                chunk[col] = chunk[col].astype('category')
                
        chunks.append(chunk)
        
    print("Concatenating chunks...")
    df = pd.concat(chunks, ignore_index=True)
    
    print(f"Dataset shape: {df.shape}")
    print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    
    print(f"Writing to {pq_file}...")
    df.to_parquet(pq_file, engine='pyarrow', index=False)
    
    print("Conversion complete.")

if __name__ == '__main__':
    main()
