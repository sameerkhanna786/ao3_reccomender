### AO3 Collection Scraper

This project includes a script to scrape works from an AO3 collection, extract metadata, and display a sorted summary.

#### Features

- Fetches all works from a specified AO3 collection.
- Extracts work details: title, author, fandom, tags, hits, and kudos.
- Sorts works by kudos and hits in descending order.
- Outputs a summary of each work.

#### Prerequisites

- Python 3.7+
- `requests` and `beautifulsoup4` libraries

#### Installation

1. Clone the repository:
    ```
    git clone https://github.com/your-username/your-repo.git
    ```
2. Navigate to the project directory:
    ```
    cd your-repo
    ```
3. Create and activate a virtual environment named `ao3_env`:
    ```
    python -m venv ao3_env
    source ao3_env/bin/activate
    ```
4. Install dependencies using `requirements.txt`:
    ```
    pip install -r requirements.txt
    ```

#### Usage

1. Run the script:
    ```
    python ao3_scraper.py
    ```
2. Enter the AO3 collection name when prompted.
3. The script will fetch and display the works sorted by kudos and hits.

> **Note:** This script is for educational purposes. Use responsibly and respect AO3's terms of service.