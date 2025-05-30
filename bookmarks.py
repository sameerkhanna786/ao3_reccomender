import requests
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import numpy as np
from urllib.parse import quote_plus
from sklearn.feature_extraction.text import TfidfVectorizer

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

            # Only include tags under "Additional Tags"
            additional_tags = []
            additional_tags_li = work.select("ul.tags.commas > li.freeforms")
            for li in additional_tags_li:
                additional_tags.extend([tag.get_text(strip=True) for tag in li.select("a.tag")])

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
                "tags": additional_tags,
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

def recommend_works_by_tags(works_data, n_topics=150, n_recommendations=5):
    """
    Recommend new AO3 works based on tag similarity using TF-IDF and LDA.
    Only recommends works not already in works_data.
    If not enough recommendations are found, iteratively remove the lowest-weighted tag and search again.
    """
    # Prepare tag documents (tags joined by comma)
    tag_docs = [", ".join(work["tags"]) for work in works_data]
    if not tag_docs or all(doc.strip() == "" for doc in tag_docs):
        print("No tags found for recommendations.")
        return []

    # Vectorize tags using TF-IDF (treat each tag as a token)
    tfidf_vectorizer = TfidfVectorizer(tokenizer=lambda x: [tag.strip() for tag in x.split(",") if tag.strip()],
                                       token_pattern=None)
    tfidf_matrix = tfidf_vectorizer.fit_transform(tag_docs)

    # Use LDA on the TF-IDF matrix
    lda = LatentDirichletAllocation(n_components=n_topics, random_state=42)
    lda_topics = lda.fit_transform(tfidf_matrix)

    # Get top topic(s) for the input works
    avg_topic_dist = np.mean(lda_topics, axis=0)
    top_topic = np.argmax(avg_topic_dist)

    # Build a set of existing work links to avoid recommending duplicates
    existing_links = set(work["link"] for work in works_data)

    # Get top tags for the top topic using TF-IDF feature names
    feature_names = np.array(tfidf_vectorizer.get_feature_names_out())
    topic_word_dist = lda.components_[top_topic]
    sorted_indices = topic_word_dist.argsort()[::-1]
    top_tag_indices = sorted_indices[:5]
    top_tags = [feature_names[i] for i in top_tag_indices]

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AO3Scraper/1.0)"
    }
    proxies = {
        "http": None,
        "https": None
    }

    recommendations = []
    tags_to_try = top_tags.copy()
    while tags_to_try:
        search_tags = ", ".join(tags_to_try)
        encoded_tags = quote_plus(search_tags)
        print(f"Searching AO3 for new works with tags: {', '.join(tags_to_try)}")

        search_url = (
            "https://archiveofourown.gay/works/search?"
            "work_search%5Bquery%5D=&"
            "work_search%5Btitle%5D=&"
            "work_search%5Bcreators%5D=&"
            "work_search%5Brevised_at%5D=&"
            "work_search%5Bcomplete%5D=&"
            "work_search%5Bcrossover%5D=&"
            "work_search%5Bsingle_chapter%5D=0&"
            "work_search%5Bword_count%5D=&"
            "work_search%5Blanguage_id%5D=&"
            "work_search%5Bfandom_names%5D=&"
            "work_search%5Brating_ids%5D=&"
            "work_search%5Bcharacter_names%5D=&"
            "work_search%5Brelationship_names%5D=&"
            f"work_search%5Bfreeform_names%5D={encoded_tags}&"
            "work_search%5Bhits%5D=&"
            "work_search%5Bkudos_count%5D=&"
            "work_search%5Bcomments_count%5D=&"
            "work_search%5Bbookmarks_count%5D=&"
            "work_search%5Bsort_column%5D=kudos_count&"
            "work_search%5Bsort_direction%5D=desc&"
            "commit=Search"
        )

        print(f"Fetching search results from: {search_url}")

        response = requests.get(search_url, headers=headers, proxies=proxies, verify=False)
        if response.status_code != 200:
            print(f"Failed to fetch search results: Status {response.status_code}")
            break

        soup = BeautifulSoup(response.content, "html.parser")
        works = soup.select("li.work.blurb.group")

        for work in works:
            link_tag = work.select_one("div.header > h4 > a")
            if not link_tag:
                continue
            href = link_tag.get("href")
            if not href:
                continue
            full_link = f"https://archiveofourown.org{href}"
            if full_link in existing_links or any(r["link"] == full_link for r in recommendations):
                continue  # Skip already known or already recommended works

            # Tags
            tags = [tag.get_text(strip=True) for tag in work.select("ul.tags.commas > li")]

            # Title
            title = link_tag.get_text(strip=True)
            # Author
            author_tag = work.select_one("a[rel=author]")
            author = author_tag.get_text(strip=True) if author_tag else "Anonymous"
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

        if len(recommendations) >= n_recommendations:
            break

        # Remove the lowest-weighted tag and try again
        if len(tags_to_try) > 1:
            tags_to_try = tags_to_try[:-1]
            print(f"Not enough recommendations found. Trying with fewer tags: {', '.join(tags_to_try)}")
        else:
            break

    return recommendations[:n_recommendations]

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

    # print_works(works_data)

    # Provide recommendations for the list of works
    if works_data:
        recommendations = recommend_works_by_tags(works_data)
        if recommendations:
            print("\nRecommended works based on your list:")
            print_works(recommendations)
        else:
            print("\nNo recommendations found.")
