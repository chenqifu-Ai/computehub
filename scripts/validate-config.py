import json

with open(r'C:\Users\Administrator\.openclaw\openclaw.json') as f:
    cfg = json.load(f)

providers = cfg.get('models', {}).get('providers', {})
print(f'providers: {len(providers)}')
for k, v in providers.items():
    print(f'  {k}: {v.get("baseUrl", "?")[:45]}')

agents_defaults = cfg.get('agents', {}).get('defaults', {})
model_primary = agents_defaults.get('model', {}).get('primary', 'none')
print(f'agent_primary: {model_primary}')

gateway = cfg.get('gateway', {})
print(f'gateway_port: {gateway.get("port", "none")}')
print(f'gateway_mode: {gateway.get("mode", "none")}')
print(f'gateway_auth_mode: {gateway.get("auth", {}).get("mode", "none")}')

aliases = agents_defaults.get('models', {})
alias_names = [v.get('alias', k.split('/')[-1]) for k, v in aliases.items()]
print(f'model_aliases: {len(alias_names)}')
print(f'first 5 aliases: {alias_names[:5]}')

print('VALID: OK')