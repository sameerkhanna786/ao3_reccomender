import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

def get_collection_work_links(collection_name):
    """Return a list of work links from the given AO3 collection."""
    base_url = f"https://archiveofourown.gay/collections/{collection_name}/works"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AO3Scraper/1.0)"
    }
    proxies = {
        "http": None,
        "https": None
    }
    page = 1
    work_links = []

    while True:
        url = base_url
        if page > 1:
            url = f"{base_url}?page={page}"
        print(f"Fetching: {url}")
        response = requests.get(url, headers=headers, proxies=proxies)
        if response.status_code != 200:
            print(f"Failed to fetch page {page}: Status {response.status_code}")
            break

        soup = BeautifulSoup(response.content, "html.parser")
        works = soup.select("li.work.blurb.group")
        if not works:
            break

        for work in works:
            link_tag = work.select_one("div.header > h4 > a")
            if not link_tag:
                continue
            href = link_tag.get("href")
            if not href:
                continue
            full_link = f"https://archiveofourown.org{href}"
            work_links.append(full_link)

        next_page = soup.select_one("li.next > a")
        if not next_page:
            break
        page += 1

    return work_links

def extract_work_info(work_url):
    # Change the URL ending to .gay in order to mitigate 503 errors and timeouts.
    # This is a workaround for AO3 rate limiting and server issues.
    # See this for more info: https://www.reddit.com/r/AO3/comments/1inmlqc/comment/mck5z8w/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button
    work_url = work_url.replace("archiveofourown.org", "archiveofourown.gay")
    """Extract and return info for a single work given its URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AO3Scraper/1.0)"
    }
    proxies = {
        "http": None,
        "https": None
    }
    response = requests.get(work_url, headers=headers, proxies=proxies)
    if response.status_code != 200:
        print(f"Failed to fetch work: {work_url}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    # Title
    title_tag = soup.select_one("h2.title.heading")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Author
    author_tag = soup.select_one("a[rel=author]")
    author = author_tag.get_text(strip=True) if author_tag else "Anonymous"

    # Tags
    tags = [tag.get_text(strip=True) for tag in soup.select("ul.tags.commas > li")]

    # Fandom
    fandom_tag = soup.select_one("h5.fandoms > a")
    fandom = fandom_tag.get_text(strip=True) if fandom_tag else ""

    # Hits and Kudos
    hits_tag = soup.select_one("dl.stats > dd.hits")
    kudos_tag = soup.select_one("dl.stats > dd.kudos")
    try:
        hits = int(hits_tag.get_text(strip=True).replace(',', '')) if hits_tag else 0
    except Exception:
        hits = 0
    try:
        kudos = int(kudos_tag.get_text(strip=True).replace(',', '')) if kudos_tag else 0
    except Exception:
        kudos = 0

    return {
        "link": work_url,
        "title": title,
        "author": author,
        "tags": tags,
        "fandom": fandom,
        "hits": hits,
        "kudos": kudos
    }

if __name__ == "__main__":
    collection_name = input("Enter AO3 collection name: ").strip()
    work_links = get_collection_work_links(collection_name)
    works_data = []
    for link in tqdm(work_links):
        info = extract_work_info(link)
        if info:
            works_data.append(info)

    # Sort by kudos, then hits (descending)
    works_data.sort(key=lambda x: (x["kudos"], x["hits"]), reverse=True)
    print(f"\nFound {len(works_data)} works in collection:\n")
    for work in works_data:
        print(work["link"])
        print(f"Title: {work['title']}")
        print(f"Author: {work['author']}")
        print(f"Fandom: {work['fandom']}")
        # print(f"Tags: {', '.join(work['tags'])}")
        print(f"Hits: {work['hits']}, Kudos: {work['kudos']}")
        print("-" * 40)
        print()