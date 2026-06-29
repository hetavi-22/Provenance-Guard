import urllib.request
import urllib.error
import json
import time

url_submit = "http://localhost:5001/submit"
url_appeal = "http://localhost:5001/appeal"
url_log = "http://localhost:5001/log"

print("--- TESTING APPEALS WORKFLOW ---")
# 1. Submit a text to get content_id
submit_data = json.dumps({
    "text": "This is a simple human written blog post about software architecture.",
    "creator_id": "creator-456"
}).encode("utf-8")

req = urllib.request.Request(
    url_submit,
    data=submit_data,
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode("utf-8"))
        content_id = res.get("content_id")
        print(f"Submission successful. content_id = {content_id}")
except Exception as e:
    print(f"Submission failed: {e}")
    exit(1)

# 2. File an appeal
appeal_data = json.dumps({
    "content_id": content_id,
    "creator_reasoning": "I wrote this myself! It has a formal style but it is entirely human and personal."
}).encode("utf-8")

req_appeal = urllib.request.Request(
    url_appeal,
    data=appeal_data,
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(req_appeal) as response:
        res_appeal = json.loads(response.read().decode("utf-8"))
        print("Appeal request successful:")
        print(json.dumps(res_appeal, indent=2))
except Exception as e:
    print(f"Appeal request failed: {e}")

# 3. Check log to verify status change
try:
    with urllib.request.urlopen(url_log) as response:
        log_res = json.loads(response.read().decode("utf-8"))
        entries = log_res.get("entries", [])
        matched = [e for e in entries if e.get("content_id") == content_id]
        if matched:
            print("\nDatabase record updated:")
            print(json.dumps(matched[0], indent=2))
        else:
            print(f"\nCould not find content_id {content_id} in log.")
except Exception as e:
    print(f"Failed to fetch logs: {e}")

print("\n--- TESTING RATE LIMITING (Sending 12 rapid requests) ---")
status_codes = []
for i in range(1, 13):
    req_lim = urllib.request.Request(
        url_submit,
        data=submit_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req_lim) as response:
            status_codes.append(response.getcode())
    except urllib.error.HTTPError as e:
        status_codes.append(e.code)
    except Exception as e:
        status_codes.append(str(e))

print(f"Status codes for 12 rapid requests: {status_codes}")
