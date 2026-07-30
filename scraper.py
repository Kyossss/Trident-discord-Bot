import logging
from bs4 import BeautifulSoup
import cloudscraper
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger('BuiltByBitBot.Scraper')

def fetch_url_sync(url: str) -> Optional[str]:
    logger.info(f"Fetching {url} using cloudscraper")
    try:
        scraper = cloudscraper.create_scraper(browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        })
        response = scraper.get(url, timeout=15.0)
        
        if response.status_code == 200:
            return response.text
        else:
            logger.error(f"Failed to fetch {url} - Status Code: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Exception while fetching {url}: {e}")
        return None

async def fetch_resource_page(resource_id: int, slug: str) -> Optional[str]:
    url = f"https://builtbybit.com/resources/{slug}.{resource_id}/"
    return await asyncio.to_thread(fetch_url_sync, url)

async def fetch_updates_page(resource_id: int, slug: str) -> Optional[str]:
    url = f"https://builtbybit.com/resources/{slug}.{resource_id}/updates"
    return await asyncio.to_thread(fetch_url_sync, url)

def parse_resource_html(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, 'lxml')
    
    # Title & Version
    title_el = soup.select_one('h1.p-title-value')
    title = ""
    version = ""
    if title_el:
        version_el = title_el.select_one('span.u-muted')
        if version_el:
            version = version_el.text.strip()
            version_el.decompose()
        title = title_el.text.strip()

    # Thumbnail
    icon_el = soup.select_one('.resourceIcon img, .avatar img')
    thumbnail_url = icon_el.get('src') if icon_el else ""
    if thumbnail_url and thumbnail_url.startswith('/'):
        thumbnail_url = "https://builtbybit.com" + thumbnail_url

    # Release Date / Last Update
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
    update_el = soup.select_one('.resourceUpdate .message-body, .message-body')
    if update_el:
        text = update_el.text.strip()
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
    
    updates_html = await fetch_updates_page(resource_id, slug)
    if updates_html:
        details['changelog'] = parse_changelog_html(updates_html)
    else:
        details['changelog'] = "Failed to fetch updates tab."
        
    return details
