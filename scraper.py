import logging
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
from typing import Dict, Any, Optional

logger = logging.getLogger('BuiltByBitBot.Scraper')

async def fetch_resource_page(resource_id: int, slug: str) -> Optional[str]:
    url = f"https://builtbybit.com/resources/{slug}.{resource_id}/"
    logger.info(f"Fetching {url}")
    
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://builtbybit.com/",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }
    
    try:
        # impersonate="chrome110" or "chrome120" handles Cloudflare TLS fingerprinting
        async with AsyncSession(impersonate="chrome110", headers=headers) as session:
            response = await session.get(url, timeout=15.0)
            
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Failed to fetch {url} - Status Code: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Exception while fetching {url}: {e}")
        return None

async def fetch_updates_page(resource_id: int, slug: str) -> Optional[str]:
    url = f"https://builtbybit.com/resources/{slug}.{resource_id}/updates"
    
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://builtbybit.com/resources/{slug}.{resource_id}/",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }
    
    try:
        async with AsyncSession(impersonate="chrome110", headers=headers) as session:
            response = await session.get(url, timeout=15.0)
            if response.status_code == 200:
                return response.text
            return None
    except Exception as e:
        logger.error(f"Exception while fetching updates for {resource_id}: {e}")
        return None

def parse_resource_html(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, 'lxml')
    
    # Title & Version
    title_el = soup.select_one('h1.p-title-value')
    title = ""
    version = ""
    if title_el:
        # Usually the title has the text, and version is in a muted span
        version_el = title_el.select_one('span.u-muted')
        if version_el:
            version = version_el.text.strip()
            # Remove version from title text
            version_el.decompose()
        title = title_el.text.strip()

    # Thumbnail
    icon_el = soup.select_one('.resourceIcon img, .avatar img')
    thumbnail_url = icon_el.get('src') if icon_el else ""
    if thumbnail_url and thumbnail_url.startswith('/'):
        thumbnail_url = "https://builtbybit.com" + thumbnail_url

    # Release Date / Last Update
    # Try to find a time tag in the resource description or info block
    date = ""
    time_el = soup.select_one('.p-description time, .resourceBody time')
    if time_el:
        date = time_el.text.strip()

    return {
        "title": title,
        "version": version,
        "thumbnail": thumbnail_url,
        "date": date
    }

def parse_changelog_html(html: str) -> str:
    soup = BeautifulSoup(html, 'lxml')
    # BuiltByBit uses XenForo Resource Manager, updates are usually in .resourceUpdate or .message-body
    update_el = soup.select_one('.resourceUpdate .message-body, .message-body')
    if update_el:
        # Extract text and truncate
        text = update_el.text.strip()
        # Discord embed field limit is 1024, description is 4096. Let's truncate to 1000.
        if len(text) > 1000:
            text = text[:997] + "..."
        return text
    return "No changelog found or could not parse."

async def get_resource_details(resource_id: int, slug: str) -> Optional[Dict[str, Any]]:
    html = await fetch_resource_page(resource_id, slug)
    if not html:
        return None
    
    details = parse_resource_html(html)
    details['url'] = f"https://builtbybit.com/resources/{slug}.{resource_id}/"
    
    # Fetch changelog if possible
    updates_html = await fetch_updates_page(resource_id, slug)
    if updates_html:
        details['changelog'] = parse_changelog_html(updates_html)
    else:
        details['changelog'] = "Failed to fetch updates tab."
        
    return details
