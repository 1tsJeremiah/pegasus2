#!/usr/bin/env python3
import sys, yaml, pathlib
p = pathlib.Path('docker-compose-master.yml')
if not p.exists():
    print('docker-compose-master.yml missing', file=sys.stderr)
    sys.exit(2)

ok = True
with p.open() as f:
    try:
        data = yaml.safe_load(f)
    except Exception as e:
        print(f'YAML parse error: {e}', file=sys.stderr)
        sys.exit(2)

services = data.get('services') or {}
networks = data.get('networks') or {}

# Checks
# 1) Required services
for name in ['pihole','unbound','traefik']:
    if name not in services:
        ok = False; print(f'missing service: {name}', file=sys.stderr)

# 2) Pi-hole image tag present
img = services.get('pihole',{}).get('image','')
if not (isinstance(img,str) and img.startswith('pihole/pihole:')):
    ok = False; print('pihole image not set or invalid', file=sys.stderr)

# 3) pihole_net network with expected subnet
pn = networks.get('pihole_net') or {}
ipam = (pn.get('ipam') or {}).get('config') or []
subnets = [c.get('subnet') for c in ipam if 'subnet' in c]
if '172.22.53.0/24' not in subnets:
    ok = False; print('pihole_net subnet missing/changed', file=sys.stderr)

# 4) Static IPs present
pihole_ips = []
unbound_ips = []
# services.pihole.networks.pihole_net.ipv4_address
pihole_net = (services.get('pihole',{}).get('networks') or {}).get('pihole_net')
if isinstance(pihole_net, dict):
    pihole_ips.append(pihole_net.get('ipv4_address'))
# services.unbound.networks.pihole_net.ipv4_address
unbound_net = (services.get('unbound',{}).get('networks') or {}).get('pihole_net')
if isinstance(unbound_net, dict):
    unbound_ips.append(unbound_net.get('ipv4_address'))
if '172.22.53.53' not in pihole_ips:
    ok = False; print('Pi-hole static IP not set to 172.22.53.53', file=sys.stderr)
if '172.22.53.54' not in unbound_ips:
    ok = False; print('Unbound static IP not set to 172.22.53.54', file=sys.stderr)

# 5) Unbound healthcheck required
uh = services.get('unbound',{}).get('healthcheck')
if not uh:
    ok = False; print('Unbound healthcheck missing', file=sys.stderr)

# 6) Autoheal labels expected on critical services
for name in ['pihole','unbound','grafana','prometheus','chroma','qdrant','traefik','webhook-server']:
    svc = services.get(name)
    if not svc:
        # not fatal for optional services
        continue
    labels = svc.get('labels') or []
    # labels can be list or dict
    found = False
    if isinstance(labels, list):
        found = any(isinstance(x,str) and 'autoheal=true' in x for x in labels)
    elif isinstance(labels, dict):
        found = labels.get('autoheal') in (True,'true','"true"')
    if not found:
        print(f'WARN: {name} missing autoheal=true label', file=sys.stderr)

sys.exit(0 if ok else 1)
