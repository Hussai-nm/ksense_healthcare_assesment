import time
import requests

BASE_URL = "https://assessment.ksensetech.com/api"
API_KEY = "ak_e9d7e70a18b048ce37b2aaa1a81b2913d8a4b5664a89fb91"

HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

def get_json(path, params=None):
    url = f"{BASE_URL}{path}"
    for attempt in range(4):  # try up to 4 times
        r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        if r.status_code in (429, 500, 503):
            time.sleep(1 + attempt)  
            continue
        r.raise_for_status()
        return r.json()

    r.raise_for_status()


def post_json(path, body):
    url = f"{BASE_URL}{path}"
    r = requests.post(url, headers=HEADERS, json=body, timeout=30)
    r.raise_for_status()
    return r.json()

def parse_bp(bp_str):
    if not isinstance(bp_str, str) or "/" not in bp_str:
        return None, None
    try:
        s, d = bp_str.split("/")
        return float(s.strip()), float(d.strip())
    except Exception:
        return None, None


def score_bp(bp_str):
    s, d = parse_bp(bp_str)
    if s is None or d is None:
        return 0  
    if s >= 140 or d >= 90:
        return 3  # Stage 2
    if (130 <= s <= 139) or (80 <= d <= 89):
        return 2  # Stage 1
    if (120 <= s <= 129) and d < 80:
        return 1  # Elevated
    if s < 120 and d < 80:
        return 0  # Normal
    return 0


def score_temp(temp):
    try:
        t = float(temp)
    except Exception:
        return 0  
    if t >= 101.0:
        return 2
    if t >= 99.6:
        return 1
    return 0


def score_age(age):
    try:
        a = float(age)
    except Exception:
        return 0  
    if a > 65:
        return 2
    if 40 <= a <= 65:
        return 1
    return 0  


def is_invalid_age(age):
    try:
        float(age)
        return False
    except Exception:
        return True


def is_invalid_temp(temp):
    try:
        float(temp)
        return False
    except Exception:
        return True


def is_invalid_bp(bp_str):
    s, d = parse_bp(bp_str)
    return s is None or d is None



def fetch_all_patients():
    patients = []
    page = 1
    while True:
        data = get_json("/patients", params={"page": page, "limit": 20})
        patients.extend(data.get("data", []))
        pagination = data.get("pagination", {}) or {}
        if not pagination.get("hasNext"):
            break
        page += 1
    return patients


def analyze(patients):
    high_risk = []
    fever = []
    data_issues = []

    for p in patients:
        pid = p.get("patient_id")

        # scores
        bp = p.get("blood_pressure")
        temp = p.get("temperature")
        age = p.get("age")

        total = score_bp(bp) + score_temp(temp) + score_age(age)

        if total >= 4:
            high_risk.append(pid)

        try:
            if float(temp) >= 99.6:
                fever.append(pid)
        except Exception:
            pass  

        if (
            age is None or temp is None or bp is None
            or is_invalid_age(age)
            or is_invalid_temp(temp)
            or is_invalid_bp(bp)
        ):
            data_issues.append(pid)

    return {
        "high_risk_patients": high_risk,
        "fever_patients": fever,
        "data_quality_issues": data_issues,
    }


def main():
    if API_KEY.startswith("PUT_") or not API_KEY:
        print("Please paste your API key at the top of this file.")
        return

    print("Fetching patients...")
    patients = fetch_all_patients()
    print(f"Got {len(patients)} patients")

    print("Scoring")
    results = analyze(patients)
    print("Counts:", {k: len(v) for k, v in results.items()})

    print("Submitting")
    resp = post_json("/submit-assessment", results)
    print("Server response:")
    print(resp)


if __name__ == "__main__":
    main()
