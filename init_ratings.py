import os
import sys
import logging
from src.scraper.ratinglists.parsers import parse_fide_rating_list, parse_cfc_rating_list, parse_uscf_rating_list
from src.scraper.ratinglists.updater import update_cfc_rating_list, update_fide_rating_list, update_uscf_rating_list
from src.scraper.ratinglists.db import reset_collections

# Parse command line arguments
DOWNLOAD_LATEST = False
RESET_DB = False

for arg in sys.argv[1:]:
    if arg == "--download":
        DOWNLOAD_LATEST = True
    elif arg == "--reset":
        RESET_DB = True

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('rating_list_init')

try:
    logger.info("Starting rating list initialization...")
    logger.info(f"Download latest ratings: {DOWNLOAD_LATEST}")
    logger.info(f"Reset database: {RESET_DB}")

    # Only reset collections if explicitly requested
    if RESET_DB:
        logger.info("Resetting database collections (--reset flag detected)...")
        reset_result = reset_collections()
        logger.info(f"Reset result: {'Successful' if reset_result else 'Failed'}")
    else:
        logger.info("Using incremental update mode - existing records will be updated, not replaced")

    if DOWNLOAD_LATEST:
        # Download and parse the latest rating lists
        logger.info("Downloading and parsing latest rating lists...")
        cfc_update = update_cfc_rating_list()
        fide_update = update_fide_rating_list()
        uscf_update = update_uscf_rating_list()
        
        logger.info(f"FIDE update: {'Successful' if fide_update else 'Failed'}")
        logger.info(f"CFC update: {'Successful' if cfc_update else 'Failed'}")
        logger.info(f"USCF update: {'Successful' if uscf_update else 'Failed'}")
        
        # Check if at least one update was successful
        if not any([cfc_update, fide_update, uscf_update]):
            logger.error("All rating list updates failed!")
            sys.exit(1)
    else:
        # Parse existing rating list files without downloading
        logger.info("Parsing existing rating list files...")
        fide_result = parse_fide_rating_list()
        cfc_result = parse_cfc_rating_list()
        uscf_result = parse_uscf_rating_list()
        
        logger.info(f"FIDE parsing: {'Successful' if fide_result else 'Failed'}")
        logger.info(f"CFC parsing: {'Successful' if cfc_result else 'Failed'}")
        logger.info(f"USCF parsing: {'Successful' if uscf_result else 'Failed'}")
        
        # Check if at least one parsing was successful
        if not any([fide_result, cfc_result, uscf_result]):
            logger.error("All rating list parsing failed! Make sure rating list files exist.")
            sys.exit(1)

    logger.info("Rating list initialization completed!")

except Exception as e:
    logger.error(f"Fatal error during initialization: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
