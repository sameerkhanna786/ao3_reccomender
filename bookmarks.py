import requests
from bs4 import BeautifulSoup

def extract_work_info_from_blurb(work, base_url="https://archiveofourown.org"):
    """Extract info for a single work from its blurb element."""
    link_tag = work.select_one("div.header > h4 > a")
    if not link_tag:
        return None
    href = link_tag.get("href")
    if not href:
        return None
    work_url = f"{base_url}{href}"

    # Title
    title = link_tag.get_text(strip=True)

    # Author
    author_tag = work.select_one("a[rel=author]")
    author = author_tag.get_text(strip=True) if author_tag else "Anonymous"

    # Tags
    tags = [tag.get_text(strip=True) for tag in work.select("ul.tags.commas > li")]

    # Fandom
    fandom_tag = work.select_one("h5.fandoms > a")
    fandom = fandom_tag.get_text(strip=True) if fandom_tag else ""

    # Hits and Kudos
    hits_tag = work.select_one("dl.stats > dd.hits")
    kudos_tag = work.select_one("dl.stats > dd.kudos")
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

def get_collection_works(collection_name):
    """Return a list of work info dicts from the given AO3 collection."""
    base_url = f"https://archiveofourown.gay/collections/{collection_name}/works"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AO3Scraper/1.0)"
    }
    proxies = {
        "http": None,
        "https": None
    }
    page = 1
    works_data = []

    while True:
        url = base_url
        if page > 1:
            url = f"{base_url}?page={page}"
        print(f"Fetching: {url}")
        response = requests.get(url, headers=headers, proxies=proxies, verify=False)
        if response.status_code != 200:
            print(f"Failed to fetch page {page}: Status {response.status_code}")
            break

        soup = BeautifulSoup(response.content, "html.parser")
        works = soup.select("li.work.blurb.group")
        if not works:
            break

        for work in works:
            info = extract_work_info_from_blurb(work)
            if info:
                works_data.append(info)

        next_page = soup.select_one("li.next > a")
        if not next_page:
            break
        page += 1

    return works_data

if __name__ == "__main__":
    collection_name = input("Enter AO3 collection name: ").strip()
    works_data = get_collection_works(collection_name)

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
