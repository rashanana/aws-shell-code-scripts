import openpyxl
import requests
import json
import time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def extract_wwids_from_excel(file_path: str, column: int = 1, sheet_name: str = None) -> list:
    wb = openpyxl.load_workbook(file_path)
    ws = wb[sheet_name] if sheet_name else wb.active
    wwids = []
    for row in ws.iter_rows(min_col=column, max_col=column, values_only=True):
        val = row[0]
        if val is None:
            continue
        wwid = str(val).strip()
        if wwid.isdigit():
            wwids.append(wwid)
    print(f"Extracted {len(wwids)} valid WWIDs")
    return wwids


def chunk(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def test_batch(wwids: list, batch_size: int, since: str = "1970-01-01") -> dict:
    """
    Test a single batch size against HR Data Hub.
    Returns result summary.
    """
    results = {
        "batch_size":     batch_size,
        "total_wwids":    len(wwids),
        "batches":        0,
        "success":        0,
        "failed":         0,
        "status_codes":   [],
        "errors":         [],
        "avg_response_ms": 0,
    }

    timings = []

    for batch in chunk(wwids, batch_size):
        results["batches"] += 1
        start = time.time()

        try:
            response = requests.get(
                HR_URL,
                headers={
                    "Authorization": f"Bearer {HR_TOKEN}",
                    "apikey":        HR_APIKEY,
                },
                params={
                    "wwid":                    ",".join(batch),
                    "last_update_date_from_dt": since,
                    "page":                    1,
                    "per_page":                1000,
                },
                verify=False,
                timeout=60,
            )

            elapsed = (time.time() - start) * 1000
            timings.append(elapsed)
            results["status_codes"].append(response.status_code)

            if response.status_code in (200, 204):
                results["success"] += 1
                print(f"  Batch {results['batches']:03d} | size={len(batch)} | status={response.status_code} | {elapsed:.0f}ms")
            else:
                results["failed"] += 1
                results["errors"].append({
                    "batch": results["batches"],
                    "status": response.status_code,
                    "response": response.text[:200]
                })
                print(f"  Batch {results['batches']:03d} | size={len(batch)} | status={response.status_code} | FAILED | {elapsed:.0f}ms")

        except Exception as e:
            results["failed"] += 1
            results["errors"].append({"batch": results["batches"], "error": str(e)})
            print(f"  Batch {results['batches']:03d} | EXCEPTION: {e}")

        time.sleep(0.5)  # small delay between batches

    results["avg_response_ms"] = round(sum(timings) / len(timings), 2) if timings else 0
    return results


def run_batch_size_tests(wwids: list, batch_sizes: list, since: str = "1970-01-01"):
    """
    Test multiple batch sizes and report which is the upper limit.
    """
    print("\n============================")
    print("Batch Size Test")
    print("============================\n")

    summary = []

    for batch_size in batch_sizes:
        print(f"\n--- Testing batch size: {batch_size} ---")
        result = test_batch(wwids, batch_size, since)
        summary.append(result)

        print(f"  Result: {result['success']}/{result['batches']} batches succeeded")
        print(f"  Avg response time: {result['avg_response_ms']}ms")

        if result["failed"] > 0:
            print(f"  FAILURES DETECTED — batch size {batch_size} may exceed API limit")
            print(f"  Errors: {json.dumps(result['errors'], indent=2)}")

    # Final summary
    print("\n============================")
    print("SUMMARY")
    print("============================")
    for r in summary:
        status = "OK" if r["failed"] == 0 else "FAILED"
        print(f"  batch_size={r['batch_size']:4d} | success={r['success']}/{r['batches']} | avg={r['avg_response_ms']}ms | {status}")

    # Find upper limit
    passing = [r for r in summary if r["failed"] == 0]
    if passing:
        upper = max(passing, key=lambda x: x["batch_size"])
        print(f"\nHighest passing batch size: {upper['batch_size']}")
    else:
        print("\nAll batch sizes failed — check credentials or API availability")


# ── Main ──────────────────────────────────────────────────
if __name__ == "__main__":
    wwids = extract_wwids_from_excel("your_file.xlsx", column=1)

    # Test these batch sizes in order
    batch_sizes = [25, 50, 100, 150, 200, 250, 300]

    run_batch_size_tests(wwids, batch_sizes, since="1970-01-01")
