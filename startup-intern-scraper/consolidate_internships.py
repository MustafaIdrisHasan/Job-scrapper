"""
Consolidate all internship CSV files into a single comprehensive list
"""

import pandas as pd
import glob
import os
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def consolidate_internships():
    """Consolidate all internship CSV files into a single comprehensive list"""
    
    # Find all CSV files
    csv_files = glob.glob("yc_jobs_*.csv")
    csv_files.extend(glob.glob("salem_laptops_*.csv"))
    csv_files.extend(glob.glob("out/internships.csv"))
    csv_files.extend(glob.glob("out/internships.xlsx"))
    
    logger.info(f"Found {len(csv_files)} CSV files to process")
    
    all_internships = []
    file_summary = []
    
    for csv_file in csv_files:
        try:
            if csv_file.endswith('.xlsx'):
                # Handle Excel files
                df = pd.read_excel(csv_file)
                logger.info(f"Processed Excel file: {csv_file} - {len(df)} records")
            else:
                # Handle CSV files
                df = pd.read_csv(csv_file)
                logger.info(f"Processed CSV file: {csv_file} - {len(df)} records")
            
            if len(df) > 0:
                # Add source file information
                df['source_file'] = csv_file
                df['processed_at'] = datetime.now().isoformat()
                
                # Standardize column names
                column_mapping = {
                    'company': 'company',
                    'role_title': 'role_title', 
                    'title': 'role_title',  # For laptop files
                    'location': 'location',
                    'pay': 'pay',
                    'price': 'pay',  # For laptop files
                    'source_url': 'source_url',
                    'url': 'source_url',  # For laptop files
                    'responsibilities': 'responsibilities',
                    'description': 'responsibilities',  # For laptop files
                    'recommended_tech_stack': 'recommended_tech_stack',
                    'posted_at': 'posted_at',
                    'scraped_at': 'scraped_at',
                    'business_score': 'business_score',
                    'server_score': 'server_score'
                }
                
                # Rename columns to standardize
                df = df.rename(columns=column_mapping)
                
                # Add to consolidated list
                all_internships.append(df)
                file_summary.append({
                    'file': csv_file,
                    'records': len(df),
                    'type': 'laptop' if 'salem' in csv_file else 'internship'
                })
                
        except Exception as e:
            logger.error(f"Error processing {csv_file}: {e}")
            continue
    
    if not all_internships:
        logger.warning("No valid CSV files found to consolidate")
        return
    
    # Combine all dataframes
    consolidated_df = pd.concat(all_internships, ignore_index=True)
    
    # Remove duplicates based on company and role_title
    initial_count = len(consolidated_df)
    consolidated_df = consolidated_df.drop_duplicates(subset=['company', 'role_title'], keep='first')
    final_count = len(consolidated_df)
    
    logger.info(f"Consolidated {initial_count} total records into {final_count} unique internships")
    
    # Sort by company and role
    consolidated_df = consolidated_df.sort_values(['company', 'role_title'])
    
    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"all_internships_consolidated_{timestamp}.csv"
    
    # Save consolidated data
    consolidated_df.to_csv(output_file, index=False)
    logger.info(f"Saved consolidated data to: {output_file}")
    
    # Generate summary report
    generate_summary_report(consolidated_df, file_summary, timestamp)
    
    return consolidated_df

def generate_summary_report(df, file_summary, timestamp):
    """Generate a comprehensive summary report"""
    
    report_file = f"internships_summary_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("INTERNSHIP SCRAPING SUMMARY REPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Unique Internships: {len(df)}\n\n")
        
        # File summary
        f.write("FILES PROCESSED:\n")
        f.write("-" * 40 + "\n")
        for file_info in file_summary:
            f.write(f"{file_info['file']}: {file_info['records']} records ({file_info['type']})\n")
        f.write("\n")
        
        # Company breakdown
        f.write("COMPANIES WITH INTERNSHIPS:\n")
        f.write("-" * 40 + "\n")
        company_counts = df['company'].value_counts()
        for company, count in company_counts.head(20).items():
            f.write(f"{company}: {count} positions\n")
        f.write("\n")
        
        # Pay analysis
        f.write("PAY ANALYSIS:\n")
        f.write("-" * 40 + "\n")
        pay_data = df[df['pay'].notna() & (df['pay'] != '')]
        if len(pay_data) > 0:
            f.write(f"Positions with pay info: {len(pay_data)}/{len(df)}\n")
            # Extract numeric pay ranges
            pay_ranges = []
            for pay in pay_data['pay']:
                if isinstance(pay, str) and '$' in pay:
                    # Extract numbers from pay strings
                    import re
                    numbers = re.findall(r'\$?(\d+(?:\.\d+)?)K?', pay)
                    if numbers:
                        pay_ranges.extend([float(n) for n in numbers])
            
            if pay_ranges:
                f.write(f"Pay range: ${min(pay_ranges):.1f}K - ${max(pay_ranges):.1f}K monthly\n")
                f.write(f"Average pay: ${sum(pay_ranges)/len(pay_ranges):.1f}K monthly\n")
        f.write("\n")
        
        # Location analysis
        f.write("LOCATION ANALYSIS:\n")
        f.write("-" * 40 + "\n")
        location_counts = df['location'].value_counts()
        for location, count in location_counts.head(10).items():
            f.write(f"{location}: {count} positions\n")
        f.write("\n")
        
        # Recent postings
        f.write("RECENT POSTINGS:\n")
        f.write("-" * 40 + "\n")
        recent_df = df[df['posted_at'].notna() & (df['posted_at'] != '')]
        if len(recent_df) > 0:
            for _, row in recent_df.head(10).iterrows():
                f.write(f"• {row['company']}: {row['role_title']} ({row['posted_at']})\n")
        f.write("\n")
        
        # All internships list
        f.write("ALL INTERNSHIPS:\n")
        f.write("-" * 40 + "\n")
        for i, (_, row) in enumerate(df.iterrows(), 1):
            f.write(f"{i:2d}. {row['company']}: {row['role_title']}\n")
            if pd.notna(row['location']) and row['location']:
                f.write(f"    Location: {row['location']}\n")
            if pd.notna(row['pay']) and row['pay']:
                f.write(f"    Pay: {row['pay']}\n")
            if pd.notna(row['source_url']) and row['source_url']:
                f.write(f"    URL: {row['source_url']}\n")
            f.write("\n")
    
    logger.info(f"Generated summary report: {report_file}")

def main():
    """Main function to run consolidation"""
    print("Consolidating all internship CSV files...")
    
    # Change to the correct directory
    os.chdir(Path(__file__).parent)
    
    try:
        consolidated_df = consolidate_internships()
        
        if consolidated_df is not None and len(consolidated_df) > 0:
            print(f"\nSuccessfully consolidated {len(consolidated_df)} unique internships!")
            print(f"Files processed: {len(glob.glob('yc_jobs_*.csv')) + len(glob.glob('salem_laptops_*.csv'))}")
            print(f"Companies: {consolidated_df['company'].nunique()}")
            print(f"Positions with pay: {len(consolidated_df[consolidated_df['pay'].notna() & (consolidated_df['pay'] != '')])}")
            
            # Show sample of results
            print(f"\nSample Internships:")
            for i, (_, row) in enumerate(consolidated_df.head(5).iterrows(), 1):
                print(f"  {i}. {row['company']}: {row['role_title']}")
                if pd.notna(row['pay']) and row['pay']:
                    print(f"     Pay: {row['pay']}")
        else:
            print("No internship data found to consolidate")
            
    except Exception as e:
        logger.error(f"Error during consolidation: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
