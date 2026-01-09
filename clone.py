#!/usr/bin/env python3

import argparse
import json
import sys
import requests
import random
from typing import Dict, List

# -------------------------------------------------
# XC CONFIG (AS REQUESTED)
# -------------------------------------------------

BASE_URL = "https://xxxxxxx.console.ves.volterra.io/api/config"
API_TOKEN = "xxxxxxxxx"

# -------------------------------------------------
# Session + Auth
# -------------------------------------------------

SESSION = requests.Session()
SESSION.headers.update({
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": f"APIToken {API_TOKEN}",
})

# -------------------------------------------------
# Helpers
# -------------------------------------------------

def die(msg):
    print(f"❌ {msg}")
    sys.exit(1)

# -------------------------------------------------
# XC Object Copier
# -------------------------------------------------

class ObjectCopier:
    def __init__(self, tenant: str, dest_namespace: str):
        self.tenant = tenant
        self.dest_namespace = dest_namespace

    # -------------------------
    # HTTP helpers
    # -------------------------

    def get(self, path: str) -> Dict:
        url = f"{BASE_URL}{path}"
        print(f"  → GET {url}")
        r = SESSION.get(url)
        r.raise_for_status()
        return r.json()

    def post(self, path: str, body: Dict):
        url = f"{BASE_URL}{path}"
        print(f"  → POST {url}")
        r = SESSION.post(url, json=body)
        if not r.ok:
            print(f"  ❌ ERROR: {r.status_code}")
            print(f"  Response: {r.text}")
            print(f"  Sent body:")
            print(json.dumps(body, indent=2))
        r.raise_for_status()
        return r.json()

    def exists(self, path: str) -> bool:
        url = f"{BASE_URL}{path}"
        r = SESSION.get(url)
        return r.status_code == 200

    # -------------------------
    # Dependency discovery
    # -------------------------

    def find_dependencies(self, lb: Dict) -> List[Dict]:
        deps = []
        seen_pools = set()  # Track unique pools to avoid duplicates
        spec = lb.get("spec", {})

        # App Firewall
        app_fw = spec.get("app_firewall")
        if isinstance(app_fw, dict) and "name" in app_fw:
            deps.append({
                "kind": "app_firewall",
                "name": app_fw["name"],
                "namespace": app_fw["namespace"]
            })
            print(f"     🔗 Found app_firewall: {app_fw['name']} ({app_fw['namespace']})")

        # Origin Pools from default_route_pools
        for pool_ref in spec.get("default_route_pools", []):
            p = pool_ref.get("pool")
            if p and "name" in p:
                pool_key = (p["name"], p["namespace"])
                if pool_key not in seen_pools:
                    seen_pools.add(pool_key)
                    deps.append({
                        "kind": "origin_pool",
                        "name": p["name"],
                        "namespace": p["namespace"]
                    })
                    print(f"     🔗 Found origin_pool: {p['name']} ({p['namespace']})")

        # Origin Pools from routes
        for route in spec.get("routes", []):
            # Handle simple_route
            simple_route = route.get("simple_route", {})
            for pool_ref in simple_route.get("origin_pools", []):
                p = pool_ref.get("pool")
                if p and "name" in p:
                    pool_key = (p["name"], p["namespace"])
                    if pool_key not in seen_pools:
                        seen_pools.add(pool_key)
                        deps.append({
                            "kind": "origin_pool",
                            "name": p["name"],
                            "namespace": p["namespace"]
                        })
                        print(f"     🔗 Found origin_pool (from route): {p['name']} ({p['namespace']})")

        return deps

    def find_healthcheck_dependency(self, pool: Dict) -> Dict:
        """Find health check dependency in origin pool"""
        spec = pool.get("spec", {})
        
        # Check for healthcheck reference
        healthcheck = spec.get("healthcheck")
        if isinstance(healthcheck, list) and len(healthcheck) > 0:
            hc = healthcheck[0]
            if isinstance(hc, dict) and "name" in hc:
                print(f"     🔗 Found healthcheck: {hc['name']} ({hc.get('namespace', 'N/A')})")
                return {
                    "kind": "healthcheck",
                    "name": hc["name"],
                    "namespace": hc.get("namespace", spec.get("namespace", ""))
                }
        
        return None

    # -------------------------
    # Object cleanup (CRITICAL)
    # -------------------------

    def clean_object(self, obj: Dict, kind: str) -> Dict:
        cleaned = {
            "metadata": obj.get("metadata", {}).copy(),
            "spec": obj.get("spec", {}).copy()
        }

        # Remove forbidden metadata fields
        for field in [
            "system_metadata",
            "resource_version",
            "referring_objects",
            "deleted_referred_objects",
            "disabled_referred_objects",
            "create_form",
            "replace_form",
        ]:
            cleaned["metadata"].pop(field, None)

        # Rewrite namespace
        cleaned["metadata"]["namespace"] = self.dest_namespace

        # -----------------------------
        # HTTP Load Balancer specific
        # -----------------------------
        if kind == "http_loadbalancer":
            # Remove runtime fields
            for field in [
                "status", "dns_info", "auto_cert_info", "cert_state",
                "create_form", "replace_form",
                "downstream_tls_certificate_expiration_timestamps",
                "internet_vip_info", "state",
            ]:
                cleaned["spec"].pop(field, None)

            # Force host_name empty
            cleaned["spec"]["host_name"] = ""

            # Remove any old https key
            cleaned["spec"].pop("https", None)

            # Add random suffix to domains
            if "domains" in cleaned["spec"]:
                suffix = random.randint(1000, 9999)
                cleaned["spec"]["domains"] = [
                    f"{domain.split('.')[0]}{suffix}.{'.'.join(domain.split('.')[1:])}"
                    for domain in cleaned["spec"]["domains"]
                ]

            # Add proper https_auto_cert block
            cleaned["spec"]["https_auto_cert"] = {
                "add_hsts": False,
                "coalescing_options": {"default_coalescing": {}},
                "connection_idle_timeout": 120000,
                "default_header": {},
                "enable_path_normalize": {},
                "header_transformation_type": {"legacy_header_transformation": {}},
                "http_protocol_options": {"http_protocol_enable_v1_v2": {}},
                "http_redirect": False,
                "no_mtls": {},
                "non_default_loadbalancer": {},
                "port": 443,
                "tls_config": {"default_security": {}},
            }

            # Remove old tls cert references
            https_cfg = cleaned["spec"]["https_auto_cert"]
            https_cfg.pop("tls_cert_params", None)
            https_cfg.pop("tls_certificates", None)

            # Update namespace references in route pools and GC spec
            for route_key in ["default_route_pools", "routes"]:
                if route_key in cleaned["spec"]:
                    if route_key == "routes":
                        # Handle routes separately as they have nested structure
                        for route in cleaned["spec"]["routes"]:
                            simple_route = route.get("simple_route", {})
                            for pool_ref in simple_route.get("origin_pools", []):
                                if "pool" in pool_ref and isinstance(pool_ref["pool"], dict):
                                    if pool_ref["pool"].get("namespace") != "shared":
                                        pool_ref["pool"]["namespace"] = self.dest_namespace
                    else:
                        # Handle default_route_pools
                        for pool_ref in cleaned["spec"][route_key]:
                            if "pool" in pool_ref and isinstance(pool_ref["pool"], dict):
                                if pool_ref["pool"].get("namespace") != "shared":
                                    pool_ref["pool"]["namespace"] = self.dest_namespace

            if "gc_spec" in cleaned["spec"]:
                gc = cleaned["spec"]["gc_spec"]
                for https_key in ["https_auto_cert", "https"]:
                    if https_key in gc:
                        gc_https = gc[https_key]
                        gc_https.pop("tls_cert_params", None)
                        gc_https.pop("tls_certificates", None)
                        gc_https["no_mtls"] = {}
                        gc_https["tls_config"] = {"default_security": {}}
                if "default_route_pools" in gc:
                    for pool_ref in gc["default_route_pools"]:
                        if "pool" in pool_ref and isinstance(pool_ref["pool"], dict):
                            if pool_ref["pool"].get("namespace") != "shared":
                                pool_ref["pool"]["namespace"] = self.dest_namespace

        # -----------------------------
        # Origin Pool specific
        # -----------------------------
        if kind == "origin_pool":
            for field in [
                "status",
                "endpoint_subsets",
            ]:
                cleaned["spec"].pop(field, None)

            # Update healthcheck namespace reference if present
            if "healthcheck" in cleaned["spec"]:
                healthcheck = cleaned["spec"]["healthcheck"]
                if isinstance(healthcheck, list) and len(healthcheck) > 0:
                    hc = healthcheck[0]
                    if isinstance(hc, dict) and hc.get("namespace") != "shared":
                        hc["namespace"] = self.dest_namespace

        # -----------------------------
        # Health Check specific
        # -----------------------------
        if kind == "healthcheck":
            for field in [
                "status",
                "referring_objects",
                "deleted_referred_objects",
                "disabled_referred_objects",
            ]:
                cleaned["spec"].pop(field, None)

        return cleaned

    # -------------------------
    # Generic copy
    # -------------------------

    def copy_object(self, kind: str, name: str, namespace: str):
        if namespace == "shared":
            print(f"\n⏭️  Skipping {kind} {name} (in 'shared' namespace)")
            return

        plural = {
            "app_firewall": "app_firewalls",
            "origin_pool": "origin_pools",
            "http_loadbalancer": "http_loadbalancers",
            "healthcheck": "healthchecks",
        }[kind]

        check_path = f"/namespaces/{self.dest_namespace}/{plural}/{name}"
        if self.exists(check_path):
            print(f"\n⏭️  Skipping {kind} {name} (already exists in {self.dest_namespace})")
            return

        print(f"\n📦 Copying {kind} {name}")

        src = self.get(f"/namespaces/{namespace}/{plural}/{name}")
        
        # If this is an origin pool, check for health check dependency
        if kind == "origin_pool":
            hc_dep = self.find_healthcheck_dependency(src)
            if hc_dep:
                self.copy_object(hc_dep["kind"], hc_dep["name"], hc_dep["namespace"])
        
        cleaned = self.clean_object(src, kind)

        self.post(f"/namespaces/{self.dest_namespace}/{plural}", cleaned)
        print(f"  ✅ Copied {kind} {name}")

    # -------------------------
    # Main LB workflow
    # -------------------------

    def copy_load_balancer(self, source_ns: str, lb_name: str):
        print("\n🔍 Fetching load balancer")
        lb = self.get(f"/namespaces/{source_ns}/http_loadbalancers/{lb_name}")

        print("\n🔍 Discovering dependencies")
        deps = self.find_dependencies(lb)

        for dep in deps:
            self.copy_object(dep["kind"], dep["name"], dep["namespace"])

        print("\n📤 Copying load balancer")
        cleaned_lb = self.clean_object(lb, "http_loadbalancer")

        self.post(
            f"/namespaces/{self.dest_namespace}/http_loadbalancers",
            cleaned_lb
        )

        print("\n🎉 LOAD BALANCER COPY COMPLETE")

# -------------------------------------------------
# CLI
# -------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Copy XC HTTP Load Balancer")
    parser.add_argument("source_namespace")
    parser.add_argument("load_balancer")
    parser.add_argument("dest_namespace")
    parser.add_argument("--tenant", default="sdc-support-yqpfidyt")

    args = parser.parse_args()

    copier = ObjectCopier(args.tenant, args.dest_namespace)
    copier.copy_load_balancer(args.source_namespace, args.load_balancer)

if __name__ == "__main__":
    main()
