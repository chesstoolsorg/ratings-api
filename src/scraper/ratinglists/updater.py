"""Updates for the FIDE and CFC rating lists.

This module handles downloading and updating the rating list files.
It can be run as a scheduled task to keep the data up-to-date.
"""

import os
import requests
import time
import datetime
import logging
import zipfile
from typing import Dict, Any, Optional

try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    print("Schedule package not installed. Automatic scheduling not available.")

from src.scraper.ratinglists.parsers import parse_fide_rating_list, parse_cfc_rating_list, parse_uscf_rating_list
from src.scraper.ratinglists.db import metadata_collection, mongo_enabled

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("rating_list_updater")

# File paths
RATING_LIST_DIR = "rating-lists"
FIDE_ZIP_PATH = os.path.join(RATING_LIST_DIR, "standard_rating_list_xml.zip")
FIDE_XML_PATH = os.path.join(RATING_LIST_DIR, "standard_rating_list.xml")
CFC_FILE_PATH = os.path.join(RATING_LIST_DIR, "tdlist.txt")
USCF_FILE_PATH = os.path.join(RATING_LIST_DIR, "uscffide.dbf")

# URLs for downloading rating lists
FIDE_DOWNLOAD_URL = os.environ.get(
    "FIDE_DOWNLOAD_URL", 
    "https://ratings.fide.com/download/standard_rating_list_xml.zip"
)
USCF_DOWNLOAD_URL = os.environ.get(
    "USCF_DOWNLOAD_URL",
    "https://www.kingregistration.com/combineddb/db"
)
CFC_DOWNLOAD_URL = os.environ.get(
    "CFC_DOWNLOAD_URL",
    "https://storage.googleapis.com/cfc-public/data/tdlist.txt"
)


def download_file(url: str, file_path: str) -> bool:
    """Download a file from a URL and save it locally.
    
    Args:
        url: The URL to download from
        file_path: Where to save the file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Make sure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        logger.info(f"Downloading {url} to {file_path}")
        
        # Download with streaming to handle potentially large files
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        
        logger.info(f"Download completed: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        return False


def extract_zip(zip_path: str, extract_dir: str) -> bool:
    """Extract a ZIP file.
    
    Args:
        zip_path: Path to the ZIP file
        extract_dir: Directory to extract to
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Make sure the extract directory exists
        os.makedirs(extract_dir, exist_ok=True)
        
        logger.info(f"Extracting {zip_path} to {extract_dir}")
        
        # Extract the file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # List all files in the ZIP
            file_list = zip_ref.namelist()
            logger.info(f"ZIP contains: {file_list}")
            
            # Extract all files
            zip_ref.extractall(extract_dir)
            
            # If we're looking for a specific file, we could check if it was extracted
            xml_files = [f for f in file_list if f.endswith('.xml')]
            if not xml_files:
                logger.warning("No XML files found in ZIP archive")
            
        logger.info(f"Extraction completed to {extract_dir}")
        return True
    except Exception as e:
        logger.error(f"Error extracting ZIP file {zip_path}: {e}")
        return False


def update_fide_rating_list() -> bool:
    """Update the FIDE rating list.
    
    1. Download the latest ZIP file
    2. Extract the XML file
    3. Parse and update the database
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Starting FIDE rating list update...")
    
    # Download the zip file
    if not download_file(FIDE_DOWNLOAD_URL, FIDE_ZIP_PATH):
        logger.error("Failed to download FIDE rating list ZIP file")
        return False
    
    # Extract the XML file from the ZIP
    logger.info(f"Extracting FIDE rating list from {FIDE_ZIP_PATH}...")
    if not extract_zip(FIDE_ZIP_PATH, RATING_LIST_DIR):
        logger.error("Failed to extract FIDE rating list from ZIP")
        return False
    
    # Check if the XML file exists after extraction
    if not os.path.exists(FIDE_XML_PATH):
        # Try to find an XML file in the directory
        xml_files = [f for f in os.listdir(RATING_LIST_DIR) if f.endswith('.xml')]
        if xml_files:
            logger.info(f"Found XML file: {xml_files[0]}")
            # Use the first XML file found
            xml_path = os.path.join(RATING_LIST_DIR, xml_files[0])
            # If it's not already named standard_rating_list.xml, rename it
            if xml_path != FIDE_XML_PATH:
                os.rename(xml_path, FIDE_XML_PATH)
        else:
            logger.error(f"No XML files found in {RATING_LIST_DIR}")
            return False
    
    # Parse and update database
    success = parse_fide_rating_list(FIDE_XML_PATH)
    
    if success:
        logger.info("FIDE rating list update completed successfully")
    else:
        logger.error("Failed to parse FIDE rating list")
    
    return success

def download_uscf_file(url: str, file_path: str) -> bool:
    """Special download function for USCF rating list which requires specific headers.
    
    Args:
        url: The URL to download from
        file_path: Where to save the file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Make sure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        logger.info(f"Downloading USCF data from {url} to {file_path}")
        
        # Add special headers that mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/octet-stream',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        # Download with streaming and proper headers
        with requests.get(url, stream=True, headers=headers) as response:
            response.raise_for_status()
            # First save the zip file to a temporary path
            zip_path = file_path + ".zip"
            with open(zip_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        
        logger.info(f"USCF download completed: {zip_path}")
        
        # Extract the zip file
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # List all files in the ZIP
                file_list = zip_ref.namelist()
                logger.info(f"USCF ZIP contains: {file_list}")
                
                # Find the DBF file
                dbf_files = [f for f in file_list if f.endswith('.dbf')]
                if not dbf_files:
                    logger.error("No DBF files found in USCF ZIP archive")
                    return False
                
                # Extract the DBF file and rename it to the target path
                zip_ref.extract(dbf_files[0], os.path.dirname(file_path))
                extracted_path = os.path.join(os.path.dirname(file_path), dbf_files[0])
                os.rename(extracted_path, file_path)
                
                # Remove the temporary zip file
                os.remove(zip_path)
                logger.info(f"USCF data extracted to {file_path}")
        except Exception as e:
            logger.error(f"Error extracting USCF zip file: {e}")
            return False
        return True
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error downloading USCF data: {e}")
        if e.response.status_code == 406:
            logger.error("Received 406 Not Acceptable error. The server likely requires specific headers or browser identification.")
        return False
    except Exception as e:
        logger.error(f"Error downloading USCF data from {url}: {e}")
        return False


def update_uscf_rating_list() -> bool:
    """Update the USCF rating list.
    
    1. Download the latest file
    2. Parse and update the database
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Starting USCF rating list update...")
    
    # Use the special download function for USCF
    if not download_uscf_file(USCF_DOWNLOAD_URL, USCF_FILE_PATH):
        logger.error("Failed to download USCF rating list")
        return False
    
    # Parse and update database
    success = parse_uscf_rating_list(USCF_FILE_PATH)
    
    if success:
        logger.info("USCF rating list update completed successfully")
    else:
        logger.error("Failed to parse USCF rating list")
    
    return success

def update_cfc_rating_list() -> bool:
    """Update the CFC rating list.
    
    1. Download the latest file
    2. Parse and update the database
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Starting CFC rating list update...")
    
    # Download the file
    if not download_file(CFC_DOWNLOAD_URL, CFC_FILE_PATH):
        logger.error("Failed to download CFC rating list")
        return False
    
    # Parse and update database
    success = parse_cfc_rating_list(CFC_FILE_PATH)
    
    if success:
        logger.info("CFC rating list update completed successfully")
    else:
        logger.error("Failed to parse CFC rating list")
    
    return success


def update_all_rating_lists() -> Dict[str, bool]:
    """Update all rating lists now.
    
    Returns:
        dict: Status of each update operation
    """
    results = {
        "fide": update_fide_rating_list(),
        "cfc": update_cfc_rating_list(),
        "uscf": update_uscf_rating_list()
    }
    return results


def schedule_updates():
    """Schedule regular updates for the rating lists."""
    if not mongo_enabled:
        logger.error("MongoDB not enabled, skipping scheduling of updates")
        return
    
    if not SCHEDULE_AVAILABLE:
        logger.error("Schedule package not available, automatic scheduling not possible")
        return
    
    # Schedule FIDE updates monthly (on the 1st of each month)
    schedule.every().month.at("00:00").do(update_fide_rating_list)
    
    # Schedule CFC updates weekly (every Monday)
    schedule.every().monday.at("00:00").do(update_cfc_rating_list)
    
    logger.info("Rating list updates scheduled")
    
    # Run the scheduler
    while True:
        schedule.run_pending()
        time.sleep(3600)  # Check every hour


if __name__ == "__main__":
    # When run directly, update all rating lists first, then start the scheduler
    logger.info("Running initial rating list updates...")
    update_all_rating_lists()
    
    if SCHEDULE_AVAILABLE:
        logger.info("Starting rating list update scheduler...")
        schedule_updates()
    else:
        logger.info("Schedule package not available, exiting after initial update")