"""
Sentinel-2 Imagery Download Script using Copernicus Data Space API
"""

import requests
from datetime import datetime
import json
import getpass
import os
import zipfile
from pathlib import Path

class Sentinel2Downloader:
    def __init__(self):
        self.api_url = "https://catalogue.dataspace.copernicus.eu/odata/v1"
        self.download_url = "https://zipper.dataspace.copernicus.eu/odata/v1"
        self.token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
        self.access_token = None
    
    @staticmethod
    def extract_tile_id(product_name):
        # Extract the tile ID from product name (e.g., 'T16SDD' from 'S2A_MSIL2A_..._T16SDD_...')
        parts = product_name.split('_')
        for part in parts:
            if part.startswith('T') and len(part) == 6:  # Tile IDs are like T16SDD
                return part
        return None
        
    def get_access_token(self, username, password):
        """Get access token for authenticated downloads"""
        data = {
            "client_id": "cdse-public",
            "username": username,
            "password": password,
            "grant_type": "password",
        }
        try:
            response = requests.post(self.token_url, data=data, timeout=30)
            response.raise_for_status()
            self.access_token = response.json()["access_token"]
            print("Successfully authenticated")
            return True
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False
    
    def search_products(self, bbox, start_date, end_date, max_cloud_cover=20):
        """
        Search for Sentinel-2 products
        
        Args:
            bbox: Bounding box as (min_lon, min_lat, max_lon, max_lat)
            start_date: Start date using the format: 'YYYY-MM-DD'
            end_date: End date using the format: 'YYYY-MM-DD'
            max_cloud_cover (optional): Maximum cloud coverage percentage (0-100)
        """
        min_lon, min_lat, max_lon, max_lat = bbox
        
        bbox = f"POLYGON(({min_lon} {min_lat},{max_lon} {min_lat},{max_lon} {max_lat},{min_lon} {max_lat},{min_lon} {min_lat}))"
        
        filter_query = (
            f"Collection/Name eq 'SENTINEL-2' and "
            f"OData.CSC.Intersects(area=geography'SRID=4326;{bbox}') and "
            f"ContentDate/Start gt {start_date}T00:00:00.000Z and "
            f"ContentDate/Start lt {end_date}T23:59:59.999Z and "
            f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le {max_cloud_cover})"
        )
        
        # filtering data 
        search_url = f"{self.api_url}/Products?$filter={filter_query}&$orderby=ContentDate/Start desc&$top=100"
        
        print(f"\nSearching for Sentinel-2 imagery...")
        print(f"  Area: ({min_lat:.4f}, {min_lon:.4f}) to ({max_lat:.4f}, {max_lon:.4f})")
        print(f"  Date range: {start_date} to {end_date}")
        print(f"  Max cloud cover: {max_cloud_cover}%")
        
        try:
            response = requests.get(search_url, timeout=30)
            response.raise_for_status()
            results = response.json()
            
            products = results.get('value', [])
            print(f"\nFound {len(products)} products")
            
            return products
            
        except Exception as e:
            print(f"Search failed: {e}")
            return []
    
    def analyze_mosaic_coverage(self, products):
        # Analyze and return different mosaic options available as *dict*
        # this dict can be obtained from search_product function

        if not products:
            return None
        
        # Group products by tile ID
        tiles_dict = {}
        for product in products:
            name = product.get('Name', '')
            tile_id = self.extract_tile_id(name)
            
            if tile_id:
                if tile_id not in tiles_dict:
                    tiles_dict[tile_id] = []
                
                # Extract cloud cover
                cloud_cover = None
                for attr in product.get('Attributes', []):
                    if attr.get('Name') == 'cloudCover':
                        cloud_cover = attr.get('Value')
                        break
                
                tiles_dict[tile_id].append({
                    'product': product,
                    'name': name,
                    'date': product.get('ContentDate', {}).get('Start', ''),
                    'cloud_cover': cloud_cover,
                    'tile_id': tile_id
                })
        
        # Find lowest cloud cover images
        best_per_tile = {}
        for tile_id, tile_products in tiles_dict.items():
            sorted_products = sorted(tile_products, key=lambda x: x['cloud_cover'] if x['cloud_cover'] is not None else 100)
            best_per_tile[tile_id] = sorted_products[0] if sorted_products else None
        
        # Check coverage
        unique_tiles = list(tiles_dict.keys())
        num_tiles = len(unique_tiles)
        complete_coverage = num_tiles > 0
        
        return {
            'unique_tiles': unique_tiles,
            'num_tiles': num_tiles,
            'tiles_dict': tiles_dict,
            'best_per_tile': best_per_tile,
            'complete_coverage': complete_coverage
        }
    
    def display_mosaic_analysis(self, analysis):
        # Display mosaic coverage analysis
        if not analysis:
            print("\nNo analysis available.")
            return
        
        print("\n" + "="*100)
        print("Mosaic analysis")
        print("="*100)
        
        num_tiles = analysis['num_tiles']
        unique_tiles = analysis['unique_tiles']
        tiles_dict = analysis['tiles_dict']
        
        print(f"\nFound {num_tiles} unique tile(s) covering your area:")
        for tile_id in sorted(unique_tiles):
            tile_products = tiles_dict[tile_id]
            print(f" * {tile_id}: {len(tile_products)} image(s) available")
        
        # Show best option per tile for cloud-free mosaic
        print("\n" + "-"*100)
        print("RECOMMENDED CLOUD-FREE MOSAIC (Best image per tile):")
        print("-"*100)
        
        best_per_tile = analysis['best_per_tile']
        total_products_for_mosaic = 0
        
        for tile_id in sorted(unique_tiles):
            best = best_per_tile.get(tile_id)
            if best:
                total_products_for_mosaic += 1
                cloud_pct = f"{best['cloud_cover']:.2f}%" if best['cloud_cover'] is not None else "N/A"
                date_str = best['date'][:10] if best['date'] else "N/A"
                
                print(f"\n[Tile {tile_id}] {best['name']}")
                print(f"Date: {date_str}")
                print(f"Cloud Cover: {cloud_pct}")
        
        # Coverage assessment
        print("\n" + "="*100)
        if num_tiles == 1:
            print("Your area fits in a single tile - no mosaicing needed!\n")
            print("You can just download the clearest image from this tile.")
        else:
            print(f"COVERAGE STATUS: Your area spans {num_tiles} tiles.")
            print(f"For a complete cloud-free mosaic, download {total_products_for_mosaic} image(s) (one per tile).")
            print(f"Note: These images may be from different dates, which is fine for cloud-free mosaics.")
        
        # Check if dates are very different
        if num_tiles > 1:
            dates = [best_per_tile[tid]['date'][:10] for tid in unique_tiles if best_per_tile.get(tid)]
            if dates:
                min_date = min(dates)
                max_date = max(dates)
                if min_date != max_date:
                    print(f"\nDate range in mosaic: {min_date} to {max_date}")
                    print(f"Different dates may show seasonal/phenological differences.")
                else:
                    print(f"\nAll tiles from same date: {min_date}")
        
        print("="*100)
    
    def get_mosaic_products(self, analysis):
        # Get the list of products needed for the cloud-free mosaic
        if not analysis or not analysis['best_per_tile']:
            return []
        
        mosaic_products = []
        for tile_id in sorted(analysis['unique_tiles']):
            best = analysis['best_per_tile'].get(tile_id)
            if best:
                mosaic_products.append(best['product'])
        
        return mosaic_products
    
    def display_products(self, products, show_tile_info=True):
        # Display product information
        if not products:
            print("\nNo products found.")
            return
        
        print("\n" + "="*100)
        print("ALL AVAILABLE PRODUCTS:")
        print("="*100)
        
        for idx, product in enumerate(products, 1):
            name = product.get('Name', 'N/A')
            product_id = product.get('Id', 'N/A')
            date = product.get('ContentDate', {}).get('Start', 'N/A')
            size = product.get('ContentLength', 0) / (1024**3)  # Convert to GB
            
            # Extract tile ID
            tile_id = self.extract_tile_id(name) if show_tile_info else None
            
            # Extract cloud cover from attributes
            cloud_cover = 'N/A'
            attributes = product.get('Attributes', [])
            for attr in attributes:
                if attr.get('Name') == 'cloudCover':
                    cloud_cover = f"{attr.get('Value', 'N/A'):.2f}%"
                    break
            
            tile_info = f" [Tile: {tile_id}]" if tile_id else ""
            
            print(f"\n[{idx}]{tile_info} {name}")
            print(f"    ID: {product_id}")
            print(f"    Date: {date}")
            print(f"    Cloud Cover: {cloud_cover}")
            print(f"    Size: {size:.2f} GB")
    
    def download_product(self, product, output_dir="downloads", extract=False):
        # Download a Sentinel-2 product
        if not self.access_token:
            print("Please authenticate first using get_access_token()")
            return False
        
        product_id = product.get('Id')
        product_name = product.get('Name')
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        output_path = os.path.join(output_dir, f"{product_name}.zip")
        
        if os.path.exists(output_path):
            print(f"File already exists: {output_path}")
            if extract:
                self._extract_product(output_path, output_dir)
            return True
        
        download_url = f"{self.download_url}/Products({product_id})/$value"
        
        print(f"\nDownloading: {product_name}")
        print(f"Destination: {output_path}")
        print(f"This may take a while... please do not turn off the program")
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(download_url, headers=headers, stream=True, timeout=300)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r  Progress: {percent:.1f}% ({downloaded/(1024**3):.2f} GB / {total_size/(1024**3):.2f} GB)", end='')
            
            print(f"\nDownload complete: {output_path}")
            
            # Extract if requested
            if extract:
                self._extract_product(output_path, output_dir)
            
            return True
            
        except Exception as e:
            print(f"\nDownload failed: {e}")
            if os.path.exists(output_path):
                os.remove(output_path)
            return False
    
    def _extract_product(self, zip_path, output_dir):
        # Extract a downloaded product zip file
        print(f"\nExtracting {os.path.basename(zip_path)}")
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get the product name without .zip
                product_name = os.path.basename(zip_path).replace('.zip', '')
                extract_path = os.path.join(output_dir, product_name)
                
                # Check if already extracted
                if os.path.exists(extract_path):
                    print(f"Already extracted to {extract_path}")
                    return
                
                print(f" Extracting to {extract_path}")
                zip_ref.extractall(extract_path)
                print(f"Extraction complete!")
                
                # Optionally remove the zip file after extraction
                remove_zip = input(f" Remove zip file to save space? (y/n): ").strip().lower()
                if remove_zip == 'y':
                    os.remove(zip_path)
                    print(f"Zip file in {zip_path} is removed")
                else:
                    print(f"Zip file will remain in {zip_path}")
                
        except Exception as e:
            print(f"Extraction failed: {e}")


def get_user_configuration():
    # Get search configuration from user
    print("\n" + "="*100)
    print("CONFIGURATION")
    print("="*100)
    
    # Ask if user wants default (relevant to this research project) or custom
    use_default = input("\nUse default configuration for Indianapolis in July 2025? (y/n): ").strip().lower()
    
    if use_default == 'y':
        # Default configuration
        bbox = (-86.3, 39.65, -85.95, 39.95)  # Indianapolis
        start_date = "2025-07-01"
        end_date = "2025-07-31"
        max_cloud_cover = 10
        
        print("\n✓ Using default configuration:")
        print(f"  Location: Indianapolis, IN")
        print(f"  Bounding Box: {bbox}")
        print(f"  Date Range: {start_date} to {end_date}")
        print(f"  Max Cloud Cover: {max_cloud_cover}%")
        
        return bbox, start_date, end_date, max_cloud_cover
    
    else:
        # Custom configuration
        print("\n" + "-"*100)
        print("CUSTOM CONFIGURATION")
        print("-"*100)
        
        # Get bounding box
        print("\nBounding Box (coordinates in decimal degrees):")
        print("\nExample: For Indianapolis use -86.3, 39.65, -85.95, 39.95")
        print("\nTo get the bouding box, you can use the links under this OSM page:") 
        print("\nhttps://wiki.openstreetmap.org/wiki/Bounding_box")
        
        while True:
            try:
                min_lon = float(input("  Min Longitude (west): ").strip())
                min_lat = float(input("  Min Latitude (south): ").strip())
                max_lon = float(input("  Max Longitude (east): ").strip())
                max_lat = float(input("  Max Latitude (north): ").strip())
                
                if min_lon >= max_lon or min_lat >= max_lat:
                    print("Invalid bounds: min values must be less than max values")
                    continue
                
                bbox = (min_lon, min_lat, max_lon, max_lat)
                break
            except ValueError:
                print("Invalid input. Please enter numeric values (in decimal degrees).")
        
        # Get date range
        print("\nDate Range:")
        while True:
            try:
                start_date = input("  Start date (YYYY-MM-DD): ").strip()
                end_date = input("  End date (YYYY-MM-DD): ").strip()
                
                # Validate date format
                datetime.strptime(start_date, "%Y-%m-%d")
                datetime.strptime(end_date, "%Y-%m-%d")
                
                if start_date >= end_date:
                    print("Start date must be before end date")
                    continue
                
                break
            except ValueError:
                print("Invalid date format. Use YYYY-MM-DD (e.g., 2025-07-01)")
        
        # Get cloud coverage
        print("\nCloud Coverage:")
        while True:
            try:
                max_cloud_cover = float(input("Maximum cloud coverage % (0-100): ").strip())
                
                if 0 <= max_cloud_cover <= 100:
                    break
                else:
                    print("Please enter a value between 0 and 100")
            except ValueError:
                print("Invalid input. Please enter an integer.")
        
        print("\nCustom configuration set:")
        print(f"  Bounding Box: {bbox}")
        print(f"  Date Range: {start_date} to {end_date}")
        print(f"  Max Cloud Cover: {max_cloud_cover}%")
        
        return bbox, start_date, end_date, max_cloud_cover


def get_output_configuration():
    # Get output directory and format preferences from user
    print("\n" + "="*100)
    print("OUTPUT CONFIGURATION")
    print("="*100)
    
    # Get output directory
    use_default_dir = input("\nUse default output directory './downloads'? (y/n): ").strip().lower()
    
    if use_default_dir == 'y':
        output_dir = "downloads"
    else:
        output_dir = input("Enter output directory path: ").strip()
        if not output_dir:
            output_dir = "downloads"
            print(f"Using default: {output_dir}")
    
    print(f"Output directory: {output_dir}")
    
    # Get extraction preference
    print("\nOutput Format:")
    print("1. Keep as .zip files (saves space)")
    print("2. Extract files (easier to work with)")
    
    while True:
        format_choice = input("Choose format (1 or 2): ").strip()
        if format_choice in ['1', '2']:
            extract = (format_choice == '2')
            break
        else:
            print("Please enter 1 or 2")
    
    if extract:
        print("Files will be extracted automatically")
    else:
        print("Files will be kept as .zip")
    
    return output_dir, extract


def main():
    # Main execution function
    
    print("="*100)
    print(" SENTINEL-2 IMAGERY DOWNLOADER")
    print("="*100)
    
    # Get user configuration
    bbox, start_date, end_date, max_cloud_cover = get_user_configuration()
    
    # Initialize downloader
    downloader = Sentinel2Downloader()
    
    # Search for products
    products = downloader.search_products(
        bbox=bbox,
        start_date=start_date,
        end_date=end_date,
        max_cloud_cover=max_cloud_cover
    )
    
    # Check if products found
    if not products:
        print("\nNo products found matching your criteria.")
        print("\nTry increasing max_cloud_cover or expanding the date range.")
        return
    
    # Analyze mosaic coverage
    analysis = downloader.analyze_mosaic_coverage(products)
    
    # Display mosaic analysis
    downloader.display_mosaic_analysis(analysis)
    
    # Check coverage and provide recommendations
    num_tiles = analysis['num_tiles']
    
    if num_tiles == 0:
        print("\nNo valid tiles identified. Please try a different search.")
        return
    
    # Display all available products
    print("\n" + "="*100)
    view_all = input("\nView all available products? (y/n): ").strip().lower()
    if view_all == 'y':
        downloader.display_products(products)
    
    # Ask user what they want to download
    print("\n" + "="*100)
    print("DOWNLOAD OPTIONS")
    print("="*100)
    print("\n1. Download recommended cloud-free mosaic (best image per tile)")
    print("2. Select specific products manually")
    print("3. Download all products")
    print("4. Exit without downloading")
    
    while True:
        choice = input("\nChoose an option (1-4): ").strip()
        if choice in ['1', '2', '3', '4']:
            break
        print("Please enter 1, 2, 3, or 4")
    
    if choice == '4':
        print("Exiting without downloading.")
        return
    
    # Get output configuration
    output_dir, extract = get_output_configuration()
    
    # Get credentials
    print("\n" + "="*100)
    print("AUTHENTICATION")
    print("="*100)
    print("You need a free account at: https://dataspace.copernicus.eu/")
    print("Register at: https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/auth")
    
    username = input("\nEnter your Copernicus username: ").strip()
    password = getpass.getpass("Enter your password: ")
    
    # Authenticate
    if not downloader.get_access_token(username, password):
        print("Authentication failed. Exiting.")
        return
    
    # Download based on choice
    print("\n" + "="*100)
    print("DOWNLOADING")
    print("="*100)
    
    if choice == '1':
        # Download recommended mosaic
        mosaic_products = downloader.get_mosaic_products(analysis)
        print(f"\nDownloading {len(mosaic_products)} product(s) for cloud-free mosaic...")
        for product in mosaic_products:
            downloader.download_product(product, output_dir, extract)
    
    elif choice == '2':
        # Manual selection
        downloader.display_products(products)
        print("\n" + "-"*100)
        
        while True:
            selection = input("\nEnter product number to download (or 'done' to finish): ").strip().lower()
            
            if selection == 'done':
                break
            
            try:
                idx = int(selection) - 1
                if 0 <= idx < len(products):
                    downloader.download_product(products[idx], output_dir, extract)
                else:
                    print(f"Invalid choice. Please enter 1-{len(products)}")
            except ValueError:
                print("Invalid input. Please enter a number or 'done'")
    
    elif choice == '3':
        # Download all
        print(f"\nDownloading all {len(products)} product(s)...")
        confirm = input(f"This will download approximately {sum(p.get('ContentLength', 0) for p in products) / (1024**3):.2f} GB. Continue? (y/n): ").strip().lower()
        
        if confirm == 'y':
            for product in products:
                downloader.download_product(product, output_dir, extract)
        else:
            print("Download cancelled.")

    # TO DO: convert .jp2 to TIF file

    # tif_convert = input(f"Would you like to convert the jp2 files into TIF file? (y/n): ").strip().lower()

    # if tif_convert == 'y':
    #     sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    #     from utils.jp2_to_tif_converter import convert_jp2_directory
    #     convert_jp2_directory(
    #         input_dir=output_dir,
    #         output_dir=output_dir + "_tif",
    #     )
    
    print("\n" + "="*100)
    print("SCRIPT COMPLETED!")
    print("="*100)
    print(f"Files saved to: {os.path.abspath(output_dir)}")

if __name__ == "__main__":
    main()
