"""
Create a clean list of only internship positions (excluding laptop data)
"""

import pandas as pd
import glob
import os
from pathlib import Path
from datetime import datetime

def create_internships_list():
    """Create a clean list of only internship positions"""
    
    # Find all YC job CSV files
    csv_files = glob.glob("yc_jobs_*.csv")
    
    print(f"Found {len(csv_files)} YC job CSV files to process")
    
    all_internships = []
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            if len(df) > 0:
                print(f"Processed {csv_file}: {len(df)} records")
                all_internships.append(df)
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")
            continue
    
    if not all_internships:
        print("No internship data found")
        return
    
    # Combine all dataframes
    consolidated_df = pd.concat(all_internships, ignore_index=True)
    
    # Remove duplicates
    initial_count = len(consolidated_df)
    consolidated_df = consolidated_df.drop_duplicates(subset=['company', 'role_title'], keep='first')
    final_count = len(consolidated_df)
    
    print(f"Consolidated {initial_count} total records into {final_count} unique internships")
    
    # Sort by company
    consolidated_df = consolidated_df.sort_values(['company', 'role_title'])
    
    # Generate output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"internships_only_{timestamp}.csv"
    
    # Save to CSV
    consolidated_df.to_csv(output_file, index=False)
    print(f"Saved to: {output_file}")
    
    # Create a simple text list
    text_file = f"internships_list_{timestamp}.txt"
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write("INTERNSHIP OPPORTUNITIES\n")
        f.write("=" * 50 + "\n")
        f.write(f"Total Positions: {len(consolidated_df)}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for i, (_, row) in enumerate(consolidated_df.iterrows(), 1):
            f.write(f"{i:2d}. {row['company']}: {row['role_title']}\n")
            if pd.notna(row['location']) and row['location']:
                f.write(f"    Location: {row['location']}\n")
            if pd.notna(row['pay']) and row['pay']:
                f.write(f"    Pay: {row['pay']}\n")
            if pd.notna(row['source_url']) and row['source_url']:
                f.write(f"    URL: {row['source_url']}\n")
            f.write("\n")
    
    print(f"Created text list: {text_file}")
    
    # Show summary
    print(f"\nSUMMARY:")
    print(f"Total Internships: {len(consolidated_df)}")
    print(f"Companies: {consolidated_df['company'].nunique()}")
    print(f"With Pay Info: {len(consolidated_df[consolidated_df['pay'].notna() & (consolidated_df['pay'] != '')])}")
    
    # Show sample
    print(f"\nSAMPLE INTERNSHIPS:")
    for i, (_, row) in enumerate(consolidated_df.head(10).iterrows(), 1):
        print(f"  {i}. {row['company']}: {row['role_title']}")
        if pd.notna(row['pay']) and row['pay']:
            print(f"     Pay: {row['pay']}")
    
    return consolidated_df

if __name__ == "__main__":
    create_internships_list()
