

---

# 🚀 XC HTTP Load Balancer Copy Script

This script copies an **F5 Distributed Cloud (XC / Volterra) HTTP Load Balancer** from one namespace to another while safely cleaning runtime fields and rebuilding TLS configuration so the object can be created via the XC API.

---

## ✨ What This Script Does

* 📦 Copies an HTTP Load Balancer across namespaces
* 🔗 Discovers and copies supported dependencies (Origin Pools, App Firewalls)
* 🧹 Removes runtime-only and forbidden fields
* 🔐 Rebuilds TLS using `https_auto_cert` (no cert reuse)
* 🔄 Rewrites namespace references
* 🌐 Randomizes domains to avoid conflicts
* ⏭️ Skips objects that already exist in the destination namespace

---

## 🚫 Objects That Will NOT Be Copied

* 🏢 **Objects in the `shared` namespace**
* 🔒 **Any TLS-related objects** (certificates, cert refs, TLS policies)
* 📦 **Objects that already exist** in the destination namespace

These are intentionally skipped to avoid unsafe reuse and conflicts.

---

## 🔧 Required Setup (Important!)

Before running the script, you **must edit the script** and set:

* 🔑 **Your XC API Token**
* 🏢 **Your XC tenant domain**

```python
BASE_URL = "https://<your-tenant>.console.ves.volterra.io/api/config"
API_TOKEN = "PUT_YOUR_API_TOKEN_HERE"
```

---

## ▶️ CLI Usage

Run the script using the following format:

```bash
python3 copy_lb.py <source_namespace> <load_balancer_name> <destination_namespace>
```

Example:

```bash
python3 copy_lb.py staging my-lb prod
```

---

## ⚠️ TLS & Certificate Notes

* 🔒 **TLS certificate objects are NOT copied**
* 🛠️ You must **manually create new TLS certificate objects**
* ⚙️ You must **manually configure TLS options** on the copied Load Balancer after creation

This is intentional to prevent invalid or unsafe certificate reuse.

---

## 🩺 Origin Pool Health Check Warning

If the script copies an **Origin Pool**:

* ❗ **You MUST remove the health check from the origin pool before running the script**
* Leaving health checks in place may cause copy failures

➡️ **Future updates** will automatically copy and rewire origin pool dependencies (including health checks).

---

## ⚠️ Gotchas

* 🌐 **Domains attached to Load Balancers are randomized**
* ✏️ Domains must be **manually reviewed and adjusted after copy**
* 🔮 **Future updates may automate domain handling**

---

## 🧪 Support & Warranty Disclaimer

* ❗ **This script is NOT officially supported by F5**
* ❗ **Support is NOT guaranteed**
* ❗ **No warranty or liability for use**

Use at your own risk and in accordance with your organization’s policies.

---

## 🛠️ Use Cases

* Cloning environments (dev → staging → prod)
* Reproducing customer configurations
* Rapid LB testing without manual rebuilds

---
