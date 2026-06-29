import json, sys, urllib.request, time

gw = "http://localhost:8282"

def get_progress(tid):
    for i in range(30):
        try:
            req = urllib.request.Request(gw + "/api/v1/tasks/progress?task_id=" + tid)
            resp = urllib.request.urlopen(req, timeout=5)
            d = json.loads(resp.read())
            if d.get("success") and d.get("data"):
                return d["data"]
        except:
            pass
        time.sleep(1)
    return None

def print_result(prefix, r):
    if not r:
        print("  [" + prefix + "] NO RESULT")
        return
    status = r.get("status","?")
    exit_code = r.get("exit_code","?")
    duration = r.get("duration","?")
    out = r.get("stdout","")
    err = r.get("stderr","")
    print("  [" + prefix + "] Status=" + str(status) + " Exit=" + str(exit_code) + " Dur=" + str(duration))
    if out:
        for line in out.split("\n")[:30]:
            safe = "".join(c if ord(c)<128 else "?" for c in line)
            print("    " + safe[:120])
    if err:
        for line in err.split("\n")[:3]:
            safe = "".join(c if ord(c)<128 else "?" for c in line)
            print("    ERR: " + safe[:120])

# Check all running tasks on wanlida-temp
task_ids = ["deep-test-001-basic", "wanlida-deep-01", "wanlida-deep-04", "wanlida-deep-11"]
for tid in task_ids:
    print("--- " + tid + " ---")
    r = get_progress(tid, 30)
    print_result(tid.split("-")[-1], r)
    print("")
