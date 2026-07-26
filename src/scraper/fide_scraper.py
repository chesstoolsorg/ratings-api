import requests
import src.scraper.functions as scraper
import src.scraper.cache as cache # Redis client
from src.scraper.cache import get_from_cache, save_to_cache


FIDE_REQUEST_TIMEOUT = 10
FIDE_UNAVAILABLE_MESSAGE = "FIDE ratings service is temporarily unavailable. Please try again later."


class FIDEServiceError(RuntimeError):
    pass


def _get_fide_html(url: str) -> str:
    try:
        response = requests.get(url, timeout=FIDE_REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text
    except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
        raise FIDEServiceError(FIDE_UNAVAILABLE_MESSAGE) from e

def get_top_players(limit: int = 100, history: bool = False) -> list[dict]:
    # Create a cache key based on function parameters (used for cache lookups)
    cache_key = f"top_players:{limit}:{history}"
    
    # Try to get from cache first
    cached_data = get_from_cache(cache_key)
    if cached_data:
        return cached_data
    
    # If not in cache, proceed with fetch
    html_doc = _get_fide_html("https://ratings.fide.com/a_top.php?list=open")
    top_players = scraper.get_top_players(html_doc)
    top_players = top_players[0:limit]

    if history == False:
        # Cache the result before returning
        save_to_cache(cache_key, top_players)
        return top_players

    for player_dict in top_players:
        fide_profile_page = f"https://ratings.fide.com/profile/{player_dict['fide_id']}"
        
        # Check if we have player history in cache
        history_cache_key = f"player_history:{player_dict['fide_id']}"
        player_history = get_from_cache(history_cache_key)
        
        if not player_history:
            # If not in cache, fetch it
            html_doc = _get_fide_html(fide_profile_page)
            player_history = scraper.get_player_history(html_doc)
            # Cache player history
            save_to_cache(history_cache_key, player_history)
        
        player_dict["history"] = player_history

    # Cache the final result with histories
    save_to_cache(cache_key, top_players)
    return top_players

def get_player_history(fide_id: str) -> list[dict]:
    # Create a cache key
    cache_key = f"player_history:{fide_id}"
    
    # Try to get from cache first
    cached_data = get_from_cache(cache_key)
    if cached_data:
        return cached_data
    
    # If not in cache, proceed with fetch
    fide_profile_page = f"https://ratings.fide.com/profile/{fide_id}"
    html_doc = _get_fide_html(fide_profile_page)
    player_history = scraper.get_player_history(html_doc)
    
    # Cache the result before returning
    save_to_cache(cache_key, player_history)
    return player_history

def get_player_info(fide_id: str, history: bool = False):
    # Create a cache key based on function parameters
    cache_key = f"player_info:{fide_id}:{history}"
    
    # Try to get from cache first
    cached_data = get_from_cache(cache_key)
    if cached_data:
        return cached_data
    
    # If not in cache, proceed with fetch
    fide_profile_page = f"https://ratings.fide.com/profile/{fide_id}"
    html_doc = _get_fide_html(fide_profile_page)
    player_info = scraper.get_player_info(html_doc)

    if history == False:
        # Cache the result before returning
        save_to_cache(cache_key, player_info)
        return player_info

    # Check if we have player history in cache
    history_cache_key = f"player_history:{fide_id}"
    player_history = get_from_cache(history_cache_key)
    
    if not player_history:
        # If not in cache, we already have the HTML doc, so just extract history
        player_history = scraper.get_player_history(html_doc)
        # Cache player history
        save_to_cache(history_cache_key, player_history)
    
    player_info["history"] = player_history
    
    # Cache the final result with history
    save_to_cache(cache_key, player_info)
    return player_info
