"""
Landsat Imagery Download Script using USGS EarthExplorer M2M API
"""

import requests
from datetime import datetime
import json
import getpass
import os
import zipfile
import tarfile
from pathlib import Path


class LandsatDownloader:
    def __init__(self):
        self.api_url = "https://m2m.cr.usgs.gov/api/api/json/stable"
        self.api_key = None

    @staticmethod
    def extract_path_row(product_name):
        """Extract the WRS-2 path/row from product name (e.g., 'LC09_L2SP_021032_...' -> '021/032')"""
        parts = product_name.split('_')
        if len(parts) >= 3:
            path_row = parts[2]
            if len(path_row) == 6 and path_row.isdigit():
                return f"{path_row[:3]}/{path_row[3:]}"
        return None

    def get_access_token(self, username, password):
        """Get API key for authenticated access"""
        login_url = f"{self.api_url}/login"
        payload = {
            "username": username,
            "password": password,
        }
        try:
            response = requests.post(login_url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            if result.get("errorCode"):
                print(f"Authentication failed: {result.get('errorMessage')}")
                return False

            self.api_key = result.get("data")
            print("Successfully authenticated")
            return True
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False

    def _api_request(self, endpoint, payload=None):
        """Make an authenticated request to the M2M API"""
        url = f"{self.api_url}/{endpoint}"
        headers = {"X-Auth-Token": self.api_key} if self.api_key else {}
        try:
            response = requests.post(url, json=payload or {}, headers=headers, timeout=60)
            response.raise_for_status()
            result = response.json()

            if result.get("errorCode"):
                print(f"API error ({endpoint}): {result.get('errorMessage')}")
                return None

            return result.get("data")
        except Exception as e:
            print(f"API request failed ({endpoint}): {e}")
            return None

    def search_products(self, bbox, start_date, end_date, max_cloud_cover=20, dataset="landsat_ot_c2_l2"):
        """
        Search for Landsat products

        Args:
            bbox: Bounding box as (min_lon, min_lat, max_lon, max_lat)
            start_date: Start date using the format: 'YYYY-MM-DD'
            end_date: End date using the format: 'YYYY-MM-DD'
            max_cloud_cover (optional): Maximum cloud coverage percentage (0-100)
            dataset: USGS dataset name (default: Landsat 8-9 Collection 2 Level-2)
        """
        min_lon, min_lat, max_lon, max_lat = bbox

        spatial_filter = {
            "filterType": "mbr",
            "lowerLeft": {"latitude": min_lat, "longitude": min_lon},
            "upperRight": {"latitude": max_lat, "longitude": max_lon},
        }

        acquisition_filter = {
            "start": start_date,
            "end": end_date,
        }

        cloud_cover_filter = {
            "min": 0,
            "max": int(max_cloud_cover),
        }

        payload = {
            "datasetName": dataset,
            "spatialFilter": spatial_filter,
            "temporalFilter": acquisition_filter,
            "cloudCoverFilter": cloud_cover_filter,
            "maxResults": 100,
        }

        print(f"\nSearching for Landsat imagery...")
        print(f"  Area: ({min_lat:.4f}, {min_lon:.4f}) to ({max_lat:.4f}, {max_lon:.4f})")
        print(f"  Date range: {start_date} to {end_date}")
        print(f"  Max cloud cover: {max_cloud_cover}%")
        print(f"  Dataset: {dataset}")

        data = self._api_request("scene-search", payload)

        if data is None:
            return []

        products = data.get("results", [])
        print(f"\nFound {len(products)} products")

        return products

    def analyze_mosaic_coverage(self, products):
        """Analyze and return different mosaic options available as dict"""
        if not products:
            return None

        # Group products by path/row
        tiles_dict = {}
        for product in products:
            name = product.get("displayId", "")
            path_row = self.extract_path_row(name)

            if path_row:
                if path_row not in tiles_dict:
                    tiles_dict[path_row] = []

                cloud_cover = product.get("cloudCover", None)

                tiles_dict[path_row].append({
                    "product": product,
                    "name": name,
                    "date": product.get("temporalCoverage", {}).get("startDate", ""),
                    "cloud_cover": cloud_cover,
                    "path_row": path_row,
                })

        # Find lowest cloud cover images
        best_per_tile = {}
        for path_row, tile_products in tiles_dict.items():
            sorted_products = sorted(
                tile_products,
                key=lambda x: x["cloud_cover"] if x["cloud_cover"] is not None else 100,
            )
            best_per_tile[path_row] = sorted_products[0] if sorted_products else None

        unique_tiles = list(tiles_dict.keys())
        num_tiles = len(unique_tiles)
        complete_coverage = num_tiles > 0

        return {
            "unique_tiles": unique_tiles,
            "num_tiles": num_tiles,
            "tiles_dict": tiles_dict,
            "best_per_tile": best_per_tile,
            "complete_coverage": complete_coverage,
        }

    def display_mosaic_analysis(self, analysis):
        """Display mosaic coverage analysis"""
        if not analysis:
            print("\nNo analysis available.")
            return

        print("\n" + "=" * 100)
        print("Mosaic analysis")
        print("=" * 100)

        num_tiles = analysis["num_tiles"]
        unique_tiles = analysis["unique_tiles"]
        tiles_dict = analysis["tiles_dict"]

        print(f"\nFound {num_tiles} unique path/row(s) covering your area:")
        for path_row in sorted(unique_tiles):
            tile_products = tiles_dict[path_row]
            print(f" * Path/Row {path_row}: {len(tile_products)} image(s) available")

        # Show best option per tile for cloud-free mosaic
        print("\n" + "-" * 100)
        print("RECOMMENDED CLOUD-FREE MOSAIC (Best image per path/row):")
        print("-" * 100)

        best_per_tile = analysis["best_per_tile"]
        total_products_for_mosaic = 0

        for path_row in sorted(unique_tiles):
            best = best_per_tile.get(path_row)
            if best:
                total_products_for_mosaic += 1
                cloud_pct = f"{best['cloud_cover']:.2f}%" if best["cloud_cover"] is not None else "N/A"
                date_str = best["date"][:10] if best["date"] else "N/A"

                print(f"\n[Path/Row {path_row}] {best['name']}")
                print(f"Date: {date_str}")
                print(f"Cloud Cover: {cloud_pct}")

        # Coverage assessment
        print("\n" + "=" * 100)
        if num_tiles == 1:
            print("Your area fits in a single path/row - no mosaicing needed!\n")
            print("You can just download the clearest image from this path/row.")
        else:
            print(f"COVERAGE STATUS: Your area spans {num_tiles} path/row(s).")
            print(f"For a complete cloud-free mosaic, download {total_products_for_mosaic} image(s) (one per path/row).")
            print(f"Note: These images may be from different dates, which is fine for cloud-free mosaics.")

        # Check if dates are very different
        if num_tiles > 1:
            dates = [best_per_tile[pr]["date"][:10] for pr in unique_tiles if best_per_tile.get(pr)]
            if dates:
                min_date = min(dates)
                max_date = max(dates)
                if min_date != max_date:
                    print(f"\nDate range in mosaic: {min_date} to {max_date}")
                    print(f"Different dates may show seasonal/phenological differences.")
                else:
                    print(f"\nAll path/rows from same date: {min_date}")

        print("=" * 100)

    def get_mosaic_products(self, analysis):
        """Get the list of products needed for the cloud-free mosaic"""
        if not analysis or not analysis["best_per_tile"]:
            return []

        mosaic_products = []
        for path_row in sorted(analysis["unique_tiles"]):
            best = analysis["best_per_tile"].get(path_row)
            if best:
                mosaic_products.append(best["product"])

        return mosaic_products

    def display_products(self, products, show_tile_info=True):
        """Display product information"""
        if not products:
            print("\nNo products found.")
            return

        print("\n" + "=" * 100)
        print("ALL AVAILABLE PRODUCTS:")
        print("=" * 100)

        for idx, product in enumerate(products, 1):
            name = product.get("displayId", "N/A")
            entity_id = product.get("entityId", "N/A")
            date = product.get("temporalCoverage", {}).get("startDate", "N/A")

            # Extract path/row
            path_row = self.extract_path_row(name) if show_tile_info else None

            cloud_cover = product.get("cloudCover", None)
            cloud_str = f"{cloud_cover:.2f}%" if cloud_cover is not None else "N/A"

            tile_info = f" [Path/Row: {path_row}]" if path_row else ""

            print(f"\n[{idx}]{tile_info} {name}")
            print(f"    Entity ID: {entity_id}")
            print(f"    Date: {date}")
            print(f"    Cloud Cover: {cloud_str}")

    def _get_download_url(self, product):
        """Request a download URL for a product via the download-request endpoint"""
        entity_id = product.get("entityId")
        dataset_name = product.get("datasetName", "landsat_ot_c2_l2")

        # First get available download options
        options_payload = {
            "datasetName": dataset_name,
            "entityIds": [entity_id],
        }
        options_data = self._api_request("download-options", options_payload)

        if not options_data:
            return None

        # Find the product bundle download (full product)
        download_id = None
        for option in options_data:
            if option.get("available") and option.get("downloadSystem") == "dds":
                product_id = option.get("id")
                download_id = product_id
                break

        # Fallback: take first available option
        if download_id is None:
            for option in options_data:
                if option.get("available"):
                    download_id = option.get("id")
                    break

        if download_id is None:
            print("No downloadable product bundle found.")
            return None

        # Request the download
        request_payload = {
            "downloads": [{"entityId": entity_id, "productId": download_id}],
        }
        request_data = self._api_request("download-request", request_payload)

        if not request_data:
            return None

        # Check available downloads
        available = request_data.get("availableDownloads", [])
        if available:
            return available[0].get("url")

        # Check if it was queued for preparation
        preparing = request_data.get("preparingDownloads", [])
        if preparing:
            print("Download is being prepared. This may take a few minutes...")
            print("You can check back or use the USGS EarthExplorer web interface.")
            return None

        return None

    def download_product(self, product, output_dir="downloads", extract=False):
        """Download a Landsat product"""
        if not self.api_key:
            print("Please authenticate first using get_access_token()")
            return False

        product_name = product.get("displayId", "unknown")

        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Landsat products are typically .tar files
        output_path_tar = os.path.join(output_dir, f"{product_name}.tar")
        output_path_zip = os.path.join(output_dir, f"{product_name}.zip")

        # Check if already downloaded
        for existing in [output_path_tar, output_path_zip]:
            if os.path.exists(existing):
                print(f"File already exists: {existing}")
                if extract:
                    self._extract_product(existing, output_dir)
                return True

        download_url = self._get_download_url(product)
        if not download_url:
            print(f"Could not obtain download URL for: {product_name}")
            return False

        print(f"\nDownloading: {product_name}")
        print(f"This may take a while... please do not turn off the program")

        try:
            headers = {"X-Auth-Token": self.api_key}
            response = requests.get(download_url, headers=headers, stream=True, timeout=300)
            response.raise_for_status()

            # Determine file extension from content headers
            content_type = response.headers.get("content-type", "")
            if "tar" in content_type:
                output_path = output_path_tar
            else:
                output_path = output_path_tar  # Default to .tar for Landsat

            print(f"Destination: {output_path}")

            total_size = int(response.headers.get("content-length", 0))
            block_size = 8192
            downloaded = 0

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(
                                f"\r  Progress: {percent:.1f}% ({downloaded / (1024**3):.2f} GB / {total_size / (1024**3):.2f} GB)",
                                end="",
                            )

            print(f"\nDownload complete: {output_path}")

            # Extract if requested
            if extract:
                self._extract_product(output_path, output_dir)

            return True

        except Exception as e:
            print(f"\nDownload failed: {e}")
            # Clean up partial file
            for p in [output_path_tar, output_path_zip]:
                if os.path.exists(p):
                    os.remove(p)
            return False

    def _extract_product(self, archive_path, output_dir):
        """Extract a downloaded product archive (tar or zip)"""
        print(f"\nExtracting {os.path.basename(archive_path)}")

        try:
            product_name = Path(archive_path).stem
            extract_path = os.path.join(output_dir, product_name)

            # Check if already extracted
            if os.path.exists(extract_path):
                print(f"Already extracted to {extract_path}")
                return

            print(f" Extracting to {extract_path}")

            if archive_path.endswith(".tar") or archive_path.endswith(".tar.gz"):
                with tarfile.open(archive_path, "r:*") as tar_ref:
                    tar_ref.extractall(extract_path)
            elif archive_path.endswith(".zip"):
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    zip_ref.extractall(extract_path)
            else:
                print(f"Unknown archive format: {archive_path}")
                return

            print(f"Extraction complete!")

            # Optionally remove the archive after extraction
            remove_archive = input(f" Remove archive file to save space? (y/n): ").strip().lower()
            if remove_archive == "y":
                os.remove(archive_path)
                print(f"Archive file {archive_path} removed")
            else:
                print(f"Archive file will remain at {archive_path}")

        except Exception as e:
            print(f"Extraction failed: {e}")

    def logout(self):
        """Logout and invalidate the API key"""
        if self.api_key:
            self._api_request("logout")
            self.api_key = None


def get_user_configuration():
    """Get search configuration from user"""
    print("\n" + "=" * 100)
    print("CONFIGURATION")
    print("=" * 100)

    # Ask if user wants default or custom
    use_default = input("\nUse default configuration for Indianapolis in July 2025? (y/n): ").strip().lower()

    if use_default == "y":
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
        print("\n" + "-" * 100)
        print("CUSTOM CONFIGURATION")
        print("-" * 100)

        # Get bounding box
        print("\nBounding Box (coordinates in decimal degrees):")
        print("\nExample: For Indianapolis use -86.3, 39.65, -85.95, 39.95")
        print("\nTo get the bounding box, you can use the links under this OSM page:")
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
                print("Invalid input. Please enter a number.")

        print("\nCustom configuration set:")
        print(f"  Bounding Box: {bbox}")
        print(f"  Date Range: {start_date} to {end_date}")
        print(f"  Max Cloud Cover: {max_cloud_cover}%")

        return bbox, start_date, end_date, max_cloud_cover


def get_output_configuration():
    """Get output directory and format preferences from user"""
    print("\n" + "=" * 100)
    print("OUTPUT CONFIGURATION")
    print("=" * 100)

    # Get output directory
    use_default_dir = input("\nUse default output directory './downloads'? (y/n): ").strip().lower()

    if use_default_dir == "y":
        output_dir = "downloads"
    else:
        output_dir = input("Enter output directory path: ").strip()
        if not output_dir:
            output_dir = "downloads"
            print(f"Using default: {output_dir}")

    print(f"Output directory: {output_dir}")

    # Get extraction preference
    print("\nOutput Format:")
    print("1. Keep as archive files (saves space)")
    print("2. Extract files (easier to work with)")

    while True:
        format_choice = input("Choose format (1 or 2): ").strip()
        if format_choice in ["1", "2"]:
            extract = format_choice == "2"
            break
        else:
            print("Please enter 1 or 2")

    if extract:
        print("Files will be extracted automatically")
    else:
        print("Files will be kept as archives")

    return output_dir, extract


def main():
    """Main execution function"""

    print("=" * 100)
    print(" LANDSAT IMAGERY DOWNLOADER")
    print("=" * 100)

    # Get user configuration
    bbox, start_date, end_date, max_cloud_cover = get_user_configuration()

    # Initialize downloader - authentication required before search for USGS M2M
    downloader = LandsatDownloader()

    # Get credentials
    print("\n" + "=" * 100)
    print("AUTHENTICATION")
    print("=" * 100)
    print("You need a free USGS EarthExplorer account.")
    print("Register at: https://ers.cr.usgs.gov/register")

    username = input("\nEnter your USGS username: ").strip()
    password = getpass.getpass("Enter your password: ")

    # Authenticate
    if not downloader.get_access_token(username, password):
        print("Authentication failed. Exiting.")
        return

    # Search for products
    products = downloader.search_products(
        bbox=bbox,
        start_date=start_date,
        end_date=end_date,
        max_cloud_cover=max_cloud_cover,
    )

    # Check if products found
    if not products:
        print("\nNo products found matching your criteria.")
        print("\nTry increasing max_cloud_cover or expanding the date range.")
        downloader.logout()
        return

    # Analyze mosaic coverage
    analysis = downloader.analyze_mosaic_coverage(products)

    # Display mosaic analysis
    downloader.display_mosaic_analysis(analysis)

    # Check coverage and provide recommendations
    num_tiles = analysis["num_tiles"]

    if num_tiles == 0:
        print("\nNo valid path/rows identified. Please try a different search.")
        downloader.logout()
        return

    # Display all available products
    print("\n" + "=" * 100)
    view_all = input("\nView all available products? (y/n): ").strip().lower()
    if view_all == "y":
        downloader.display_products(products)

    # Ask user what they want to download
    print("\n" + "=" * 100)
    print("DOWNLOAD OPTIONS")
    print("=" * 100)
    print("\n1. Download recommended cloud-free mosaic (best image per path/row)")
    print("2. Select specific products manually")
    print("3. Download all products")
    print("4. Exit without downloading")

    while True:
        choice = input("\nChoose an option (1-4): ").strip()
        if choice in ["1", "2", "3", "4"]:
            break
        print("Please enter 1, 2, 3, or 4")

    if choice == "4":
        print("Exiting without downloading.")
        downloader.logout()
        return

    # Get output configuration
    output_dir, extract = get_output_configuration()

    # Download based on choice
    print("\n" + "=" * 100)
    print("DOWNLOADING")
    print("=" * 100)

    if choice == "1":
        # Download recommended mosaic
        mosaic_products = downloader.get_mosaic_products(analysis)
        print(f"\nDownloading {len(mosaic_products)} product(s) for cloud-free mosaic...")
        for product in mosaic_products:
            downloader.download_product(product, output_dir, extract)

    elif choice == "2":
        # Manual selection
        downloader.display_products(products)
        print("\n" + "-" * 100)

        while True:
            selection = input("\nEnter product number to download (or 'done' to finish): ").strip().lower()

            if selection == "done":
                break

            try:
                idx = int(selection) - 1
                if 0 <= idx < len(products):
                    downloader.download_product(products[idx], output_dir, extract)
                else:
                    print(f"Invalid choice. Please enter 1-{len(products)}")
            except ValueError:
                print("Invalid input. Please enter a number or 'done'")

    elif choice == "3":
        # Download all
        print(f"\nDownloading all {len(products)} product(s)...")
        confirm = input("Continue? (y/n): ").strip().lower()

        if confirm == "y":
            for product in products:
                downloader.download_product(product, output_dir, extract)
        else:
            print("Download cancelled.")

    # Logout
    downloader.logout()

    print("\n" + "=" * 100)
    print("SCRIPT COMPLETED!")
    print("=" * 100)
    print(f"Files saved to: {os.path.abspath(output_dir)}")


if __name__ == "__main__":
    main()
