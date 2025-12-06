"""
Download census tract boundaries for Franklin County, Ohio.
Uses Census TIGER/Line shapefiles via HTTP download.
"""

import urllib.request
import zipfile
from pathlib import Path
import shutil

def download_census_tracts():
    """Download Franklin County census tract boundaries."""
    
    output_dir = Path("backend/data/census_tracts")
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Check if already downloaded
    shapefile_path = output_dir / "tl_2023_39_tract.shp"
    if shapefile_path.exists():
        print(f"✓ Census tracts already downloaded at {shapefile_path}")
        return shapefile_path
    
    print("="*80)
    print("DOWNLOADING CENSUS TRACT BOUNDARIES")
    print("="*80)
    
    # Census TIGER/Line 2023 Ohio Tracts
    url = "https://www2.census.gov/geo/tiger/TIGER2023/TRACT/tl_2023_39_tract.zip"
    
    print(f"\nDownloading from: {url}")
    print("This may take a minute...")
    
    zip_path = output_dir / "census_tracts.zip"
    
    try:
        # Download with progress
        urllib.request.urlretrieve(url, zip_path)
        print(f"✓ Downloaded to {zip_path}")
        
        # Extract
        print(f"\nExtracting files...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
        
        print(f"✓ Extracted to {output_dir}")
        
        # Clean up zip file
        zip_path.unlink()
        
        # Verify shapefile exists
        if shapefile_path.exists():
            print(f"\n✓ Successfully downloaded census tract shapefile!")
            print(f"  Location: {shapefile_path}")
            
            # Count files
            files = list(output_dir.glob("*"))
            print(f"  Files: {len(files)} (shp, shx, dbf, prj, etc.)")
            
            return shapefile_path
        else:
            print(f"\n✗ Shapefile not found after extraction")
            return None
            
    except Exception as e:
        print(f"\n✗ Error downloading: {e}")
        print("\nManual download instructions:")
        print("1. Visit: https://www.census.gov/cgi-bin/geo/shapefiles/index.php")
        print("2. Select: 2023 → Census Tracts → Ohio")
        print("3. Download and extract to: backend/data/census_tracts/")
        return None

def download_census_block_groups():
    """Download Franklin County census block groups (finer resolution)."""
    
    output_dir = Path("backend/data/census_block_groups")
    output_dir.mkdir(exist_ok=True, parents=True)
    
    shapefile_path = output_dir / "tl_2023_39_bg.shp"
    if shapefile_path.exists():
        print(f"✓ Block groups already downloaded at {shapefile_path}")
        return shapefile_path
    
    print("\n" + "="*80)
    print("DOWNLOADING CENSUS BLOCK GROUPS")
    print("="*80)
    
    url = "https://www2.census.gov/geo/tiger/TIGER2023/BG/tl_2023_39_bg.zip"
    
    print(f"\nDownloading from: {url}")
    
    zip_path = output_dir / "block_groups.zip"
    
    try:
        urllib.request.urlretrieve(url, zip_path)
        print(f"✓ Downloaded")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
        
        zip_path.unlink()
        
        if shapefile_path.exists():
            print(f"✓ Block groups downloaded to {output_dir}")
            return shapefile_path
        else:
            return None
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

if __name__ == "__main__":
    print("Downloading Census geography files for spatial analysis...")
    print("This enables matching traffic segments to demographics/employment.\n")
    
    # Download census tracts (broader areas)
    tract_path = download_census_tracts()
    
    # Download block groups (finer resolution, better for employment data)
    bg_path = download_census_block_groups()
    
    print("\n" + "="*80)
    print("DOWNLOAD SUMMARY")
    print("="*80)
    
    if tract_path:
        print(f"✓ Census Tracts: {tract_path}")
    else:
        print("✗ Census Tracts: Failed")
    
    if bg_path:
        print(f"✓ Block Groups: {bg_path}")
    else:
        print("✗ Block Groups: Failed")
    
    if tract_path or bg_path:
        print("\nNext steps:")
        print("1. Run: python backend/integrate_spatial_data.py")
        print("2. This will match your traffic segments to census areas")
        print("3. Employment and demographic data will be added to predictions")
