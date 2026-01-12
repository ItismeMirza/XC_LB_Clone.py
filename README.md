---
# 🚀 XC HTTP Load Balancer Copy Script
This script copies an **F5 Distributed Cloud (XC / Volterra) HTTP Load Balancer** from one namespace to another while safely cleaning runtime fields and rebuilding TLS configuration so the object can be created via the XC API.
---
## ✨ What This Script Does
* 📦 Copies an HTTP Load Balancer across namespaces
* 🔗 Discovers and copies dependencies (Origin Pools, App Firewalls, Health Checks)
* 🧹 Removes runtime-only and forbidden fields
* 🔐 Supports both automatic certificates and custom TLS certificates
* 🔄 Rewrites namespace references automatically
* 🌐 Allows custom domain name configuration
* ⏭️ Skips objects that already exist in the destination namespace
* 🐳 Can run as a Docker container
---
## 🚫 Objects That Will NOT Be Copied
* 🏢 **Objects in the `shared` namespace** - These are global resources
* 📦 **Objects that already exist** in the destination namespace - Prevents duplicates
These are intentionally skipped to avoid conflicts and maintain consistency.
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

### Basic Syntax
```bash
python3 xc_lb_copier.py <source_namespace> <load_balancer_name> <destination_namespace> <domain_name> [OPTIONS]
```

### Required Arguments
| Argument | Description | Example |
|----------|-------------|---------|
| `source_namespace` | Namespace containing the load balancer | `staging` |
| `load_balancer_name` | Name of the load balancer to copy | `my-lb` |
| `destination_namespace` | Destination namespace | `prod` |
| `domain_name` | Domain name for the copied LB | `prod.example.com` |

### Optional Arguments
| Option | Description | Default |
|--------|-------------|---------|
| `--tenant` | XC Tenant ID | `sdc-support-yqpfidyt` |
| `--certificate` | Custom certificate name | None (uses auto-cert) |

### Examples

**With automatic certificate:**
```bash
python3 xc_lb_copier.py staging my-lb prod prod.example.com
```

**With custom certificate:**
```bash
python3 xc_lb_copier.py staging my-lb prod prod.example.com --certificate prod-cert
```

**With custom tenant:**
```bash
python3 xc_lb_copier.py staging my-lb prod prod.example.com --tenant my-tenant-id
```

---
## 🐳 Docker Usage

### Build the Docker Image
```bash
docker build -t xc-lb-copier .
```

### Run with Docker

**With automatic certificate:**
```bash
docker run --rm xc-lb-copier staging my-lb prod prod.example.com
```

**With custom certificate:**
```bash
docker run --rm xc-lb-copier staging my-lb prod prod.example.com --certificate prod-cert
```

---
## ⚠️ Important Domain Name Note

**Before running the script**, you must ensure the domain name you're using is unique:

1. **Option 1:** Change the domain name on the source load balancer before copying
2. **Option 2:** Use a completely different domain name in the CLI argument

The script will set the domain name to exactly what you specify in the `<domain_name>` argument. If the domain conflicts with an existing load balancer, the API will reject the creation.

---
## 🔐 TLS & Certificate Options

### Automatic Certificate (Default)
If you don't specify `--certificate`, the script uses XC's automatic certificate management:
* ✅ Automatically provisions Let's Encrypt certificates
* ✅ No manual certificate management needed
* ✅ Certificates auto-renew

### Custom Certificate
If you specify `--certificate`:
* 🔍 Script verifies the certificate exists in the destination namespace
* 🔐 Configures the load balancer to use your custom certificate
* ⚠️ You must create the certificate in the destination namespace first

---
## 🩺 Health Check Support

The script now automatically handles health checks:
* ✅ **Discovers health checks** attached to origin pools
* ✅ **Copies health checks** before copying origin pools
* ✅ **Updates namespace references** automatically

No manual intervention needed for health checks!

---
## 🔄 What Gets Copied

When you copy a load balancer, the script automatically copies:
1. **Health Checks** (if referenced by origin pools)
2. **Origin Pools** (from default routes and custom routes)
3. **App Firewalls** (if configured)
4. **The Load Balancer itself**

All namespace references are updated to point to the destination namespace.

---
## ⚠️ Gotchas

* 🌐 **Domain names must be unique** - Ensure no conflicts before running
* 🔐 **Custom certificates must exist** in destination namespace before use
* 📝 **API token must have proper permissions** for both source and destination namespaces
* 🏢 **Shared namespace objects** are referenced but not copied

---
## 🧪 Support & Warranty Disclaimer

* ❗ **This script is NOT officially supported by F5**
* ❗ **Support is NOT guaranteed**
* ❗ **No warranty or liability for use**

Use at your own risk and in accordance with your organization's policies.

---
## 🛠️ Use Cases

* Cloning environments (dev → staging → prod)
* Reproducing customer configurations
* Rapid LB testing without manual rebuilds
* Migrating load balancers between namespaces
* Creating test environments with custom certificates

---
## 📋 Prerequisites

* Python 3.6+
* `requests` library: `pip install requests`
* Valid XC API token with read/write permissions
* Docker (optional, for containerized usage)

---
