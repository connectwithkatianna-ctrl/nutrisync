import requests
from bs4 import BeautifulSoup
import redis
import os

# --- Configurations ---
EWG_URL = "https://www.ewg.org/research/secret-gras-how-100-food-chemicals-bypassed-government-safety-review"
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

def get_redis_client():
    """Establish connection to the production Redis instance."""
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True
    )

def get_ewg_secret_list():
    """Scrapes the EWG article for flagged 'Secret GRAS' chemicals."""
    print("Fetching EWG Secret GRAS list...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Nutrisync/1.0'}
    
    try:
        response = requests.get(EWG_URL, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        flagged_ingredients = []
        for item in soup.find_all('strong'): 
            text = item.get_text(strip=True).lower()
            if len(text) > 2 and " " in text: 
                flagged_ingredients.append(text)
                
        flagged_ingredients.extend(["tara flour", "qmatrix", "teavigo"])
        return list(set(flagged_ingredients))
    
    except Exception as e:
        print(f"EWG Scrape failed: {e}")
        return []

def get_fda_approved_list():
    """Fetches the FDA GRAS notices to see what is actually reviewed."""
    print("Fetching FDA GRAS Inventory...")
    # Mocking FDA 'No Questions' list for brevity
    return ["ascorbic acid", "citric acid", "whey protein isolate"] 

def sync_to_redis():
    ewg_list = get_ewg_secret_list()
    fda_list = get_fda_approved_list()
    r = get_redis_client()
    
    updated_count = 0
    
    print("Starting Redis synchronization...")
    for ingredient in ewg_list:
        if ingredient not in fda_list:
            redis_key = f"ingred:tier4:{ingredient.replace(' ', '_')}"
            
            mapping = {
                "name": ingredient.title(),
                "synonyms": ingredient,
                "tier": "4",
                "allergen_type": "secret_gras",
                "source": "ewg"
            }
            
            r.hset(redis_key, mapping=mapping)
            updated_count += 1
            
    print(f"Successfully synced {updated_count} loophole ingredients to Redis.")

if __name__ == "__main__":
    sync_to_redis()
