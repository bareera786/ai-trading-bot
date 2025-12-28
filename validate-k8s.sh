#!/bin/bash

# Kubernetes Manifest Validation Script
# Validates all YAML files before deployment

set -e

echo "🔍 Validating Kubernetes manifests..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check if kubectl can validate (connected to cluster)
if kubectl cluster-info &>/dev/null; then
    KUBECTL_VALIDATION=true
    print_success "Connected to Kubernetes cluster - full validation enabled"
else
    KUBECTL_VALIDATION=false
    print_warning "Not connected to cluster - basic YAML validation only"
fi

# Check if yamllint is available (optional)
if command -v yamllint &> /dev/null; then
    YAMLLINT_AVAILABLE=true
    print_success "yamllint available for enhanced validation"
else
    YAMLLINT_AVAILABLE=false
    print_warning "yamllint not available - install for better validation"
fi

# Validate YAML syntax and Kubernetes schema
validate_yaml() {
    local file=$1
    local filename=$(basename "$file")

    echo "Validating $filename..."

    # Check YAML syntax (handle multi-document files)
    if python3 -c "
import yaml
import sys
try:
    with open('$file', 'r') as f:
        yaml.safe_load_all(f)
    print('YAML_VALID')
except Exception as e:
    print(f'YAML_ERROR: {e}')
    sys.exit(1)
    " | grep -q "YAML_VALID"; then
        print_success "$filename: YAML syntax valid"
    else
        print_error "$filename: Invalid YAML syntax"
        return 1
    fi

    # Use kubectl to validate against Kubernetes schema (if connected)
    if [ "$KUBECTL_VALIDATION" = true ]; then
        if kubectl apply --dry-run=client -f "$file" &>/dev/null; then
            print_success "$filename: Valid Kubernetes manifest"
        else
            print_error "$filename: Invalid Kubernetes manifest"
            kubectl apply --dry-run=client -f "$file" 2>&1 | head -10
            return 1
        fi
    else
        print_success "$filename: YAML syntax valid (cluster validation skipped)"
    fi

    # Optional: yamllint for style checking
    if [ "$YAMLLINT_AVAILABLE" = true ]; then
        if yamllint "$file" &>/dev/null; then
            print_success "$filename: YAML style check passed"
        else
            print_warning "$filename: YAML style issues (non-blocking)"
        fi
    fi

    return 0
}

# Files to validate
files=(
    "k8s/optimized-deployment.yaml"
    "k8s/service.yaml"
    "k8s/configmap.yaml"
    "k8s/secret.yaml"
    "k8s/pvc.yaml"
    "k8s/ingress.yaml"
    "k8s/hpa.yaml"
    "k8s/network-policy.yaml"
    "k8s/pdb.yaml"
)

# Validate all files
failed_files=()
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        if ! validate_yaml "$file"; then
            failed_files+=("$file")
        fi
    else
        print_error "$file: File not found"
        failed_files+=("$file")
    fi
done

# Summary
echo
echo "📊 Validation Summary:"
echo "======================"

if [ ${#failed_files[@]} -eq 0 ]; then
    print_success "All manifests are valid!"
    echo
    print_success "Ready for deployment with: ./deploy-k8s.sh"
else
    print_error "Found ${#failed_files[@]} invalid files:"
    for file in "${failed_files[@]}"; do
        echo "  - $file"
    done
    echo
    print_error "Please fix the issues before deploying."
    exit 1
fi

# Additional checks
echo
echo "🔍 Additional Checks:"
echo "====================="

# Check for placeholder values
if grep -q "your-" k8s/secret.yaml; then
    print_warning "secret.yaml contains placeholder values - update before production"
fi

if grep -q "your-" k8s/ingress.yaml; then
    print_warning "ingress.yaml contains placeholder domain - update before production"
fi

# Check resource limits
if grep -q "512Mi" k8s/optimized-deployment.yaml && grep -q "250m" k8s/optimized-deployment.yaml; then
    print_success "Resource optimization applied correctly"
else
    print_warning "Resource limits may not be optimized"
fi

# Check for health probes
if grep -q "livenessProbe" k8s/optimized-deployment.yaml && grep -q "readinessProbe" k8s/optimized-deployment.yaml; then
    print_success "Health probes configured"
else
    print_warning "Health probes not found"
fi

echo
print_success "Validation complete!"