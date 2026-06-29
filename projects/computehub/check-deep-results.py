import json, sys, urllib.request

gw = "http://localhost:8282"
task_ids = ["deep-test-001-basic", "wanlida-deep-01", "wanlida-deep-04", "wanlida-deep-11"]

for tid in task_ids:
    print("=== " + tid + " ===")
    try:
        req = urllib.request.Request(gw + "/api/v1/tasks/progress?task_id=" + tid)
        resp = urllib.request.urlopen(req, timeout=10)
        d = json.loads(resp.read())
        if d.get("success") and d.get("data"):
            r = d["data"]
            print("  status=" + str(r.get("status","?")))
            print("  exit_code=" + str(r.get("exit_code","?")))
            print("  duration=" + str(r.get("duration","?")))
            out = r.get("stdout", "")
            err = r.get("stderr", "")
            if out:
                for line in out.split("\n")[:15]:
                    safe = "".join(c if ord(c)<128 else "?" for c in line)
                    print("  " + safe[:120])
            if err:
                for line in err.split("\n")[:3]:
                    safe = "".join(c if ord(c)<128 else "?" for c in line)
                    print("  ERR: " + safe[:120])
        else:
            print("  no data")
    except Exception as e:
        print("  error: " + str(e))
    print("")
