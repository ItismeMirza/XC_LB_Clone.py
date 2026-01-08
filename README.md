# XC_LB_Clone.py
Copies an F5 XC HTTP Load Balancer between namespaces, automatically handling dependencies, cleaning runtime-only fields, rebuilding TLS using https_auto_cert, rewriting namespaces, and avoiding invalid certificate references to ensure safe, repeatable creation via the XC API.
