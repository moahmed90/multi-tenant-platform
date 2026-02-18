#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import shutil

TIERS = {
    "small": {
        "replicas": 1,
        "memory_request": "128Mi",
        "memory_limit": "256Mi",
        "cpu_request": "100m",
        "cpu_limit": "200m"
    },
    "standard": {
        "replicas": 2,
        "memory_request": "256Mi",
        "memory_limit": "512Mi",
        "cpu_request": "200m",
        "cpu_limit": "400m"
    },
    "large": {
        "replicas": 3,
        "memory_request": "512Mi",
        "memory_limit": "1Gi",
        "cpu_request": "500m",
        "cpu_limit": "1000m"
    }
}

def create_namespace_yaml(tenant_name):
    """Generate namespace YAML"""
    return f"""---
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-{tenant_name}
  labels:
    tenant: {tenant_name}
"""

def create_deployment_yaml(tenant_name, tier):
    """Generate deployment YAML"""
    config = TIERS[tier]
    return f"""---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  namespace: tenant-{tenant_name}
  labels:
    app: web
    tenant: {tenant_name}
spec:
  replicas: {config['replicas']}
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
        tenant: {tenant_name}
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "{config['memory_request']}"
            cpu: "{config['cpu_request']}"
          limits:
            memory: "{config['memory_limit']}"
            cpu: "{config['cpu_limit']}"
"""

def create_service_yaml(tenant_name):
    """Generate service YAML"""
    return f"""---
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
  namespace: tenant-{tenant_name}
  labels:
    app: web
    tenant: {tenant_name}
spec:
  type: ClusterIP
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 80
    protocol: TCP
"""

def create_configmap_yaml(tenant_name):
    """Generate configmap YAML"""
    return f"""---
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: tenant-{tenant_name}
  labels:
    tenant: {tenant_name}
data:
  database_host: "postgres.example.com"
  database_port: "5432"
  app_mode: "production"
  log_level: "info"
"""

def create_argocd_application_yaml(tenant_name):
    """Generate ArgoCD Application YAML"""
    return f"""---
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: {tenant_name}-tenant
  namespace: argocd
  labels:
    tenant: {tenant_name}
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/moahmed90/multi-tenant-platform
    targetRevision: main
    path: gitops/tenants/{tenant_name}
  destination:
    server: https://kubernetes.default.svc
    namespace: tenant-{tenant_name}
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas
"""

def create_tenant(name, tier):
    """Create new tenant environment"""
    print(f"🚀 Provisioning tenant: {name} (tier: {tier})")
    
    
    tenant_dir = Path(f"gitops/tenants/{name}")
    tenant_dir.mkdir(parents=True, exist_ok=True)
    
    
    (tenant_dir / "namespace.yaml").write_text(create_namespace_yaml(name))
    (tenant_dir / "deployment.yaml").write_text(create_deployment_yaml(name, tier))
    (tenant_dir / "service.yaml").write_text(create_service_yaml(name))
    (tenant_dir / "configmap.yaml").write_text(create_configmap_yaml(name))
    
    print(f"  ✅ Created Kubernetes manifests in gitops/tenants/{name}/")
    
    
    argocd_dir = Path("gitops/argocd")
    argocd_dir.mkdir(parents=True, exist_ok=True)
    (argocd_dir / f"application-{name}.yaml").write_text(
        create_argocd_application_yaml(name)
    )
    
    print(f"  ✅ Created ArgoCD application: gitops/argocd/application-{name}.yaml")
    
    
    print(f"\n📝 Tenant Created Successfully!")
    print(f"   Name: {name}")
    print(f"   Tier: {tier}")
    print(f"   Replicas: {TIERS[tier]['replicas']}")
    print(f"   Resources: {TIERS[tier]['memory_limit']} RAM, {TIERS[tier]['cpu_limit']} CPU")
    print(f"\n🔄 Next steps:")
    print(f"   1. Review files: ls -la gitops/tenants/{name}/")
    print(f"   2. Commit: git add gitops/")
    print(f"   3. Push: git push")
    print(f"   4. ArgoCD will auto-deploy!")

def delete_tenant(name):
    """Delete tenant environment"""
    print(f"🗑️  Deleting tenant: {name}")
    
    tenant_dir = Path(f"gitops/tenants/{name}")
    argocd_file = Path(f"gitops/argocd/application-{name}.yaml")
    
    if not tenant_dir.exists():
        print(f"  ❌ Tenant '{name}' not found")
        return
    
    print(f"  This will delete:")
    print(f"   - gitops/tenants/{name}/")
    print(f"   - gitops/argocd/application-{name}.yaml")
    
    confirm = input("\n  Are you sure? (yes/no): ")
    if confirm.lower() != "yes":
        print("  ❌ Cancelled")
        return
    
    
    if tenant_dir.exists():
        shutil.rmtree(tenant_dir)
        print(f"  ✅ Deleted tenant directory")
    
    if argocd_file.exists():
        argocd_file.unlink()
        print(f"  ✅ Deleted ArgoCD application")
    
    print(f"\n📝 Next steps:")
    print(f"   1. Commit: git add -A")
    print(f"   2. Commit: git commit -m 'Remove tenant {name}'")
    print(f"   3. Push: git push")

def list_tenants():
    """List all tenants"""
    print("📋 Provisioned Tenants:\n")
    
    tenants_dir = Path("gitops/tenants")
    if not tenants_dir.exists():
        print("  No tenants found")
        return
    
    for tenant_dir in sorted(tenants_dir.iterdir()):
        if tenant_dir.is_dir() and not tenant_dir.name.startswith('.'):
            print(f"  • {tenant_dir.name}")
            
            
            deployment_file = tenant_dir / "deployment.yaml"
            if deployment_file.exists():
                content = deployment_file.read_text()
                if "replicas: 1" in content:
                    tier = "small"
                elif "replicas: 3" in content:
                    tier = "large"
                else:
                    tier = "standard"
                print(f"    Tier: {tier}")

def main():
    parser = argparse.ArgumentParser(
        description="Multi-tenant provisioning tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
   
    create_parser = subparsers.add_parser("create", help="Create new tenant")
    create_parser.add_argument("--name", required=True, help="Tenant name")
    create_parser.add_argument(
        "--tier", 
        choices=TIERS.keys(), 
        default="standard",
        help="Resource tier (small/standard/large)"
    )
    
    
    delete_parser = subparsers.add_parser("delete", help="Delete tenant")
    delete_parser.add_argument("--name", required=True, help="Tenant name")
    
    
    list_parser = subparsers.add_parser("list", help="List all tenants")
    
    args = parser.parse_args()
    
    if args.command == "create":
        create_tenant(args.name, args.tier)
    elif args.command == "delete":
        delete_tenant(args.name)
    elif args.command == "list":
        list_tenants()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
