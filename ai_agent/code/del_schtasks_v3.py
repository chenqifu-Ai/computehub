#!/usr/bin/env python3
"""Delete stale schtasks using pre-encoded PS command (no $ in Python source)"""
import json, urllib.request

b64 = "cwBjAGgAdABhAHMAawBzACAALwBkAGUAbABlAHQAZQAgAC8AdABuACAAIgBcAEMASABTAHQAYQByAHQAIgAgAC8AZgAKAGUAYwBoAG8AIABPAEsAXwBDAEgAUwB0AGEAcgB0AAoAcwBjAGgAdABhAHMAawBzACAALwBkAGUAbABlAHQAZQAgAC8AdABuACAAIgBcAEMASABMAG8AZwBvAG4AIgAgAC8AZgAKAGUAYwBoAG8AIABPAEsAXwBDAEgATABvAGcAbwBuAAoAcwBjAGgAdABhAHMAawBzACAALwBkAGUAbABlAHQAZQAgAC8AdABuACAAIgBcAEMAbwBtAHAAdQB0AGUASAB1AGIAUwB0AGEAcgB0ACIAIAAvAGYACgBlAGMAaABvACAATwBLAF8AQwBvAG0AcAB1AHQAZQBIAHUAYgBTAHQAYQByAHQACgBzAGMAaAB0AGEAcwBrAHMAIAAvAGQAZQBsAGUAdABlACAALwB0AG4AIAAiAFwAQwBvAG0AcAB1AHQAZQBIAHUAYgBMAG8AZwBvAG4AIgAgAC8AZgAKAGUAYwBoAG8AIABPAEsAXwBDAG8AbQBwAHUAdABlAEgAdQBiAEwAbwBnAG8AbgAKAHMAYwBoAHQAYQBzAGsAcwAgAC8AZABlAGwAZQB0AGUAIAAvAHQAbgAgACIAXABjAG8AbQBwAHUAdABlAGgAdQBiAC0AdQBwAGcAcgBhAGQAZQAiACAALwBmAAoAZQBjAGgAbwAgAE8ASwBfAGMAbwBtAHAAdQB0AGUAaAB1AGIALQB1AHAAZwByAGEAZABlAAoA"

task = {
    'node_id': 'Windows-mobile',
    'command': f'powershell -EncodedCommand {b64}',
    'timeout': 20,
    'priority': 10,
    'max_retries': 1
}

req = urllib.request.Request(
    'http://36.250.122.43:8282/api/v1/tasks/submit',
    data=json.dumps(task).encode(),
    headers={'Content-Type': 'application/json'}
)
result = json.loads(urllib.request.urlopen(req, timeout=15).read())
print(json.dumps(result, indent=2, ensure_ascii=False))
