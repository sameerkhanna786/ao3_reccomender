import requests
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import numpy as np

def get_collection_works(collection_name):
    """Yield info dicts for each work in the given AO3 collection."""
    base_url = f"https://archiveofourown.gay/collections/{collection_name}/works"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AO3Scraper/1.0)"
    }
    proxies = {
        "http": None,
        "https": None
    }
    page = 1

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
            # Extract link
            link_tag = work.select_one("div.header > h4 > a")
            if not link_tag:
                continue
            href = link_tag.get("href")
            if not href:
                continue
            full_link = f"https://archiveofourown.org{href}"

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

            # Summary
            summary_tag = work.select_one("blockquote.userstuff.summary")
            summary = summary_tag.get_text(strip=True) if summary_tag else ""

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

            yield {
            "link": full_link,
            "title": title,
            "author": author,
            "tags": tags,
            "fandom": fandom,
            "summary": summary,
            "hits": hits,
            "kudos": kudos
            }

        next_page = soup.select_one("li.next > a")
        if not next_page:
            break
        page += 1

def extract_work_info(work_url):
    # Change the URL ending to .gay in order to mitigate 503 errors and timeouts.
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

    # Summary
    summary_tag = soup.select_one("div.summary blockquote.userstuff")
    summary = summary_tag.get_text(strip=True) if summary_tag else ""

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
        "summary": summary,
        "hits": hits,
        "kudos": kudos
    }

def print_works(works_data):
    # Sort by kudos, then hits (descending)
    works_data.sort(key=lambda x: (x["kudos"], x["hits"]), reverse=True)
    print(f"\nFound {len(works_data)} works:\n")
    for work in works_data:
        print(work["link"])
        print(f"Title: {work['title']}")
        print(f"Author: {work['author']}")
        print(f"Fandom: {work['fandom']}")
        print(f"Summary: {work['summary']}")
        print(f"Tags: {', '.join(work['tags'])}")
        print(f"Hits: {work['hits']}, Kudos: {work['kudos']}")
        print("-" * 40)
        print()

def recommend_works_by_tags(works_data, n_topics=10, n_recommendations=5):
    """
    Recommend new AO3 works based on tag similarity using LDA.
    Only recommends completed works not already in works_data.
    """
    # Prepare tag documents (tags joined by comma, not space)
    tag_docs = [", ".join(work["tags"]) for work in works_data]
    if not tag_docs or all(doc.strip() == "" for doc in tag_docs):
        print("No tags found for LDA recommendations.")
        return []

    # Vectorize tags as phrases (treat each tag as a token)
    vectorizer = CountVectorizer(tokenizer=lambda x: [tag.strip() for tag in x.split(",") if tag.strip()],
                                 token_pattern=None)
    tag_matrix = vectorizer.fit_transform(tag_docs)

    # Fit LDA
    lda = LatentDirichletAllocation(n_components=n_topics, random_state=42)
    lda_topics = lda.fit_transform(tag_matrix)

    # Get top topic(s) for the input works
    avg_topic_dist = np.mean(lda_topics, axis=0)
    top_topic = np.argmax(avg_topic_dist)

    # Build a set of existing work links to avoid recommending duplicates
    existing_links = set(work["link"] for work in works_data)

    # Query AO3 for new works by searching for top tags in the top topic
    feature_names = np.array(vectorizer.get_feature_names_out())
    topic_word_dist = lda.components_[top_topic]
    top_tag_indices = topic_word_dist.argsort()[::-1][:5]
    top_tags = [feature_names[i] for i in top_tag_indices]

    # Build AO3 search URL using top tags (joined by '+') and completed works only
    search_tags = "+".join(top_tags)
    search_url = (
        "https://archiveofourown.gay/works"
        "?utf8=✓"
        f"&work_search%5Bother_tag_names%5D={search_tags}"
        "&work_search%5Bcomplete%5D=T"
        "&sort_column=kudos_count"
        "&commit=Search"
    )

    print(f"Searching AO3 for new completed works with tags: {', '.join(top_tags)}")
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AO3Scraper/1.0)"
    }
    proxies = {
        "http": None,
        "https": None
    }
    response = requests.get(search_url, headers=headers, proxies=proxies, verify=False)
    if response.status_code != 200:
        print(f"Failed to fetch search results: Status {response.status_code}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    works = soup.select("li.work.blurb.group")
    recommendations = []
    for work in works:
        # Check for completed status (look for <span class="iswip"> or <dl class="stats">)
        is_complete = False
        status_tag = work.select_one("dl.stats > dt.status")
        if status_tag and "Completed" in status_tag.find_next_sibling("dd").get_text(strip=True):
            is_complete = True
        # AO3 also marks incomplete works with <span class="iswip">, so skip if present
        if work.select_one("span.iswip"):
            is_complete = False
        if not is_complete:
            continue

        link_tag = work.select_one("div.header > h4 > a")
        if not link_tag:
            continue
        href = link_tag.get("href")
        if not href:
            continue
        full_link = f"https://archiveofourown.org{href}"
        if full_link in existing_links:
            continue  # Skip already known works

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
        # Summary
        summary_tag = work.select_one("blockquote.userstuff.summary")
        summary = summary_tag.get_text(strip=True) if summary_tag else ""
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

        recommendations.append({
            "link": full_link,
            "title": title,
            "author": author,
            "tags": tags,
            "fandom": fandom,
            "summary": summary,
            "hits": hits,
            "kudos": kudos
        })

        if len(recommendations) >= n_recommendations:
            break

    return recommendations

if __name__ == "__main__":
    choice = input("Do you want to provide a list of work URLs (enter 'list') or a collection name (enter 'collection')? ").strip().lower()
    works_data = []
    if choice == "collection":
        collection_name = input("Enter AO3 collection name: ").strip()
        works_data = list(get_collection_works(collection_name))
    elif choice == "list":
        urls = input("Enter AO3 work URLs separated by commas: ").strip().split(",")
        for url in urls:
            url = url.strip()
            if url:
                info = extract_work_info(url)
                if info:
                    works_data.append(info)
    else:
        print("Invalid choice. Please enter 'list' or 'collection'.")
        exit(1)

    print_works(works_data)

    # Provide recommendations for the list of works
    if works_data:
        recommendations = recommend_works_by_tags(works_data)
        if recommendations:
            print("\nRecommended works based on your list:")
            print_works(recommendations)
        else:
            print("\nNo recommendations found.")
