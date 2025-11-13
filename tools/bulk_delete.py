import csv
import sys
import requests

API_URL = "https://data.digitalwaters.org/deletedata/"
API_KEY = "6706Nyl7CXpyQ12l3fUt67gcWdWOIvA7q9Vpo8JVSzGBy7lQ8Tq4MnKdkJ34MafoafEdjSeEVjfxsD2mV90fkB8f4nb4i6kdEaYS6hZcOqACZrXcfFTbmwxPxpcMycmu"
CHUNK_SIZE = 20


def readIdsFromCsv(csvPath):
    ids = []
    with open(csvPath, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            for cell in row:
                cell = cell.strip()
                if not cell:
                    continue
                if not cell.isdigit():
                    print(f"Skipping non-numeric value: {cell}")
                    continue
                ids.append(int(cell))
    return ids


def chunkList(items, chunkSize):
    for i in range(0, len(items), chunkSize):
        yield items[i : i + chunkSize]


def deleteIds(idChunk):
    # Build query like ?IDsToDelete=12345&IDsToDelete=98765&...
    params = [("IDsToDelete", str(recId)) for recId in idChunk]

    headers = {}
    if API_KEY:
        headers["x-api-key"] = API_KEY

    # If your endpoint is POST (FastAPI @app.post), keep POST.
    # If it's actually GET-only, change to requests.get(...)
    response = requests.post(API_URL, params=params, headers=headers, timeout=30)

    print("=" * 60)
    print(f"Deleting {len(idChunk)} IDs: {', '.join(map(str, idChunk))}")
    print(f"Status: {response.status_code}")
    try:
        print("Response JSON:", response.json())
    except ValueError:
        print("Response text:", response.text)
    print("=" * 60)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} path/to/ids.csv")
        sys.exit(1)

    csvPath = sys.argv[1]
    ids = readIdsFromCsv(csvPath)

    print(f"Loaded {len(ids)} IDs from {csvPath}")

    for idChunk in chunkList(ids, CHUNK_SIZE):
        deleteIds(idChunk)


if __name__ == "__main__":
    main()
