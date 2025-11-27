# Channel System: Real-World Scenario

## Executive Summary

This document walks through a **real-world scenario** showing how channels are used in practice. We'll follow a platform team updating the API archetype configuration and rolling it out to services across different environments.

---

## Scenario: Updating API Archetype Security Configuration

### **The Situation**

The platform team needs to:
1. **Update security settings** in the API archetype (add stricter security context)
2. **Test the changes** in integration environment first
3. **Gradually roll out** to pre-production
4. **Deploy to production** after validation
5. **Have ability to rollback** if issues occur

**Without channels**: Would need to update every service individually, or risk deploying untested changes to production.

**With channels**: Can test in `next` channel, then promote to `stable` when ready.

---

## Timeline: Complete Workflow

### **Day 1: Development & Initial Testing**

#### **Step 1: Platform Team Makes Configuration Changes**

**What Happens**:
- Platform engineer updates the API archetype security configuration
- Changes include stricter security context, read-only root filesystem, etc.

**Files Changed**:
```yaml
# kustomize/archetype/api/deployment.yaml
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
        - name: app
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
```

**Git Actions**:
```bash
git checkout -b feature/api-security-hardening
git add kustomize/archetype/api/deployment.yaml
git commit -m "feat: Add stricter security context to API archetype"
git push origin feature/api-security-hardening
```

**Current Channel State**:
```yaml
# kustomize/catalog/channels.yaml
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.06-rc1
```

**Services Using Channels**:
```yaml
# kustomize/catalog/services.yaml
services:
  - name: payment-processor
    channel: stable  # Production service
    
  - name: account-service
    channel: stable  # Production service
    
  - name: test-api-service
    channel: next    # Test service (uses next channel)
```

**Status**:
- ✅ Changes committed to feature branch
- ✅ No impact on existing services (they use `stable` channel)
- ✅ Test service can opt-in to test changes

---

#### **Step 2: Test Service Opts-In to New Configuration**

**What Happens**:
- `test-api-service` is already using `next` channel
- Platform team updates `next` channel to point to feature branch

**Channel Update**:
```yaml
# kustomize/catalog/channels.yaml (temporary for testing)
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/heads/feature/api-security-hardening  # Point to feature branch
```

**Git Actions**:
```bash
git add kustomize/catalog/channels.yaml
git commit -m "chore: Point next channel to security hardening branch"
git push
```

**Impact**:
- `test-api-service` (using `next`) → Now uses new security configuration
- `payment-processor` and `account-service` (using `stable`) → Still use old configuration
- No disruption to production services

**CI/CD Behavior**:
- CI detects change in `channels.yaml`
- Regenerates manifests for `test-api-service` (uses `next` channel)
- Does NOT regenerate manifests for services using `stable` channel
- Commits new manifests to `generated/test-api-service/` directory

**Result**:
- ✅ `test-api-service` gets new security configuration
- ✅ Production services unaffected
- ✅ Can test changes in isolation

---

### **Day 2-3: Integration Testing**

#### **Step 3: Merge to Develop and Create RC Tag**

**What Happens**:
- Feature branch is merged to `develop` branch
- Platform team creates a Release Candidate (RC) tag for testing

**Git Actions**:
```bash
# Merge feature branch
git checkout develop
git merge feature/api-security-hardening
git push origin develop

# Create RC tag
git tag config-2025.11.07-rc1
git push origin config-2025.11.07-rc1
```

**Channel Update**:
```yaml
# kustomize/catalog/channels.yaml
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.07-rc1  # Updated to RC tag
```

**Git Actions**:
```bash
git add kustomize/catalog/channels.yaml
git commit -m "chore: Update next channel to config-2025.11.07-rc1"
git push
```

**Impact**:
- `test-api-service` (using `next`) → Now uses RC tag (more stable than feature branch)
- All services using `next` channel get the RC version
- Production services still use `stable` (old configuration)

**Testing**:
- `test-api-service` deployed to `int-stable` environment
- Security team validates new security settings
- Performance testing confirms no regressions
- All tests pass ✅

**Result**:
- ✅ RC version validated in integration environment
- ✅ Ready for pre-production testing
- ✅ Production services still safe

---

### **Day 4: Pre-Production Validation**

#### **Step 4: Promote Next Channel for Pre-Production**

**What Happens**:
- Platform team wants to test in `pre-stable` environment
- Some services in pre-stable can opt-in to `next` channel

**Service Updates** (Optional - services can opt-in):
```yaml
# kustomize/catalog/services.yaml
services:
  - name: payment-processor
    channel: stable  # Production service, stays on stable
    
  - name: account-service
    channel: next    # Opt-in to next for pre-stable testing
    # ... other config
```

**Or Use Environment Default**:
```yaml
# kustomize/catalog/env-pins.yaml
defaultChannel:
  pre-stable: next  # Pre-stable defaults to next channel
```

**Impact**:
- Services in `pre-stable` using `next` channel → Get RC version
- Services in `pre-stable` using `stable` channel → Stay on old version
- Production services (all using `stable`) → Unaffected

**Testing in Pre-Stable**:
- `account-service` deployed to `pre-stable` with new security config
- Security audit passes
- Load testing confirms stability
- All validation passes ✅

**Result**:
- ✅ Pre-production validation successful
- ✅ Ready for production promotion
- ✅ Production services still safe

---

### **Day 5: Production Release**

#### **Step 5: Create Stable Tag and Promote**

**What Happens**:
- All testing complete, ready for production
- Platform team creates stable tag and promotes `next` → `stable`

**Git Actions**:
```bash
# Create stable tag from RC
git tag config-2025.11.07
git push origin config-2025.11.07
```

**Channel Promotion**:
```yaml
# kustomize/catalog/channels.yaml (BEFORE)
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.07-rc1

# kustomize/catalog/channels.yaml (AFTER)
channels:
  stable: refs/tags/config-2025.11.07  # Promoted from next
  next: refs/tags/config-2025.11.08-rc1  # New next for future changes
```

**Git Actions**:
```bash
git add kustomize/catalog/channels.yaml
git commit -m "chore: Promote config-2025.11.07 to stable channel"
git push
```

**Impact - IMMEDIATE**:
- ✅ All services using `stable` channel → Now use `config-2025.11.07`
- ✅ `payment-processor` (using `stable`) → Gets new security configuration
- ✅ `account-service` (switched to `stable`) → Gets new security configuration
- ✅ All production services get updated configuration

**CI/CD Behavior**:
1. CI detects change in `channels.yaml`
2. Identifies all services using `stable` channel:
   - `payment-processor`
   - `account-service`
   - Any other services using `stable`
3. Regenerates manifests for all these services
4. Commits to `generated/` directory:
   - `generated/payment-processor/int-stable/euw1/manifests.yaml`
   - `generated/payment-processor/prod/euw1/manifests.yaml`
   - `generated/account-service/int-stable/euw1/manifests.yaml`
   - `generated/account-service/prod/euw1/manifests.yaml`
   - etc.

**Deployment**:
- Next deployment of any service using `stable` channel will use new manifests
- New security configuration applied automatically
- No manual intervention needed

**Result**:
- ✅ All production services get new security configuration
- ✅ Single channel update affects all services
- ✅ Consistent configuration across all services

---

### **Day 6: Issue Detected (Rollback Scenario)**

#### **Step 6: Rollback to Previous Stable Version**

**What Happens**:
- Issue detected in production (e.g., compatibility problem)
- Platform team needs to rollback quickly

**Channel Rollback**:
```yaml
# kustomize/catalog/channels.yaml (BEFORE - problematic)
channels:
  stable: refs/tags/config-2025.11.07  # Current (has issue)
  next: refs/tags/config-2025.11.08-rc1

# kustomize/catalog/channels.yaml (AFTER - rolled back)
channels:
  stable: refs/tags/config-2025.11.06  # Rolled back to previous
  next: refs/tags/config-2025.11.07  # Keep new version in next for fixing
```

**Git Actions**:
```bash
git add kustomize/catalog/channels.yaml
git commit -m "chore: Rollback stable channel to config-2025.11.06"
git push
```

**Impact - IMMEDIATE**:
- ✅ All services using `stable` channel → Revert to `config-2025.11.06`
- ✅ `payment-processor` → Back to old (working) configuration
- ✅ `account-service` → Back to old (working) configuration
- ✅ Issue resolved without touching individual services

**CI/CD Behavior**:
1. CI detects change in `channels.yaml`
2. Regenerates manifests for all services using `stable`
3. New manifests use old configuration (from `config-2025.11.06`)
4. Next deployment reverts to previous working state

**Result**:
- ✅ Quick rollback (single channel update)
- ✅ All services revert together
- ✅ No service-by-service updates needed

---

## Comparison: With Channels vs Without Channels

### **Scenario: Without Channels**

**What Would Happen**:

1. **Update Every Service Individually**:
   ```yaml
   # Would need to update each service
   services:
     - name: payment-processor
       configRef: refs/tags/config-2025.11.07  # Hardcoded
     - name: account-service
       configRef: refs/tags/config-2025.11.07  # Hardcoded
     - name: user-service
       configRef: refs/tags/config-2025.11.07  # Hardcoded
     # ... 50+ more services
   ```

2. **Problems**:
   - ❌ Need to update 50+ services individually
   - ❌ Easy to miss services
   - ❌ Inconsistent versions across services
   - ❌ Rollback requires updating all services again
   - ❌ No easy way to test new config before production

3. **Rollback**:
   - ❌ Update all 50+ services again
   - ❌ Risk of missing some services
   - ❌ Time-consuming and error-prone

### **Scenario: With Channels**

**What Happens**:

1. **Single Channel Update**:
   ```yaml
   # Update once, affects all services
   channels:
     stable: refs/tags/config-2025.11.07  # Single update
   ```

2. **Benefits**:
   - ✅ Update once, all services get change
   - ✅ Consistent versions across all services
   - ✅ Easy rollback (change channel mapping)
   - ✅ Can test in `next` channel before production
   - ✅ Gradual rollout possible

3. **Rollback**:
   - ✅ Change channel mapping once
   - ✅ All services revert together
   - ✅ Fast and reliable

---

## Real-World Use Cases

### **Use Case 1: Security Patch Rollout**

**Situation**: Critical security vulnerability in base configuration needs immediate patching.

**With Channels**:
1. Create security patch branch
2. Point `next` channel to patch branch
3. Test in integration environment
4. Create stable tag: `config-2025.11.07-security-patch`
5. Update `stable` channel → All services get patch immediately
6. **Time**: 2-3 hours from patch to production

**Without Channels**:
1. Update each service individually
2. Risk missing services
3. Inconsistent patching
4. **Time**: Days to weeks

---

### **Use Case 2: Gradual Feature Rollout**

**Situation**: New feature (e.g., new monitoring component) needs gradual rollout.

**With Channels**:
1. Create feature branch with new component
2. Point `next` channel to feature branch
3. Select services opt-in to `next` channel:
   ```yaml
   services:
     - name: payment-processor
       channel: next  # Opt-in to new feature
     - name: account-service
       channel: stable  # Stay on stable
   ```
4. Test with `payment-processor` in production
5. If successful, promote `next` → `stable`
6. All services get feature automatically

**Without Channels**:
1. Would need to manually update each service
2. No easy way to test subset of services
3. All-or-nothing approach

---

### **Use Case 3: Environment-Specific Configuration**

**Situation**: Production needs older, proven configuration while dev/test can use latest.

**With Channels**:
```yaml
# Services
services:
  - name: payment-processor
    channel: stable  # Production uses stable

# Environment defaults
envPins:
  prod: refs/tags/config-2025.10.28  # Prod pinned to older version
  int-stable: refs/tags/config-2025.11.06  # Dev uses newer

defaultChannel:
  prod: stable  # But stable points to newer, so...
  # Actually, envPins override, so prod uses config-2025.10.28
```

**Result**:
- Production uses older, proven configuration
- Dev/test uses newer configuration
- Easy to update each independently

---

### **Use Case 4: Multi-Region Deployment**

**Situation**: DR region needs newer configuration for failover scenarios.

**With Channels**:
```yaml
# Services
services:
  - name: payment-processor
    channel: stable  # Default

# Region pins
regionPins:
  euw2:
    prod: refs/tags/config-2025.11.07  # DR region gets newer config
```

**Result**:
- Primary region (euw1) uses `stable` → `config-2025.11.06`
- DR region (euw2) uses region pin → `config-2025.11.07` (newer)
- DR region ready for failover with latest config

---

## Channel Resolution in Practice

### **Example: payment-processor Service**

**Service Definition**:
```yaml
services:
  - name: payment-processor
    channel: stable
    regions: [euw1, euw2]
    enabledIn: [int-stable, prod]
```

**Resolution Flow**:

**For int-stable + euw1**:
```
1. Service specifies: channel: stable
2. Lookup channels.yaml: stable → refs/tags/config-2025.11.07
3. Use configuration from config-2025.11.07 tag
```

**For prod + euw2**:
```
1. Service specifies: channel: stable
2. Check region pins: euw2.prod → refs/tags/config-2025.11.08 (override!)
3. Use configuration from config-2025.11.08 tag (newer for DR)
```

**Result**: Same service, different config versions per environment/region.

---

## Best Practices from Real Scenarios

### **1. Always Test in Next Channel First**

**Practice**:
- Never promote directly to `stable`
- Always test in `next` channel first
- Create RC tags for testing

**Why**:
- Catches issues before production
- Allows rollback without affecting production
- Enables gradual validation

### **2. Use Environment Pins for Production Stability**

**Practice**:
```yaml
envPins:
  prod: refs/tags/config-2025.10.28  # Prod pinned to older version
```

**Why**:
- Production stability is critical
- Can test new config in dev/test first
- Easy to update prod when ready

### **3. Monitor Channel Usage**

**Practice**:
- Track which services use which channels
- Alert on services using outdated channels
- Regular channel audits

**Why**:
- Ensures consistency
- Identifies services that need updates
- Prevents configuration drift

### **4. Document Channel Changes**

**Practice**:
- Document why channel was updated
- Include testing results in commit messages
- Maintain changelog of channel updates

**Why**:
- Provides audit trail
- Helps with troubleshooting
- Enables knowledge sharing

---

## Summary

**Channels provide**:
- ✅ **Centralized control**: Update once, affect all services
- ✅ **Gradual rollout**: Test in `next`, promote to `stable`
- ✅ **Easy rollback**: Change channel mapping
- ✅ **Consistency**: All services using same channel get same config
- ✅ **Flexibility**: Services can opt-in to different channels

**Real-World Benefits**:
- **Security patches**: Deploy to all services in hours, not days
- **Feature rollouts**: Test with subset, then promote to all
- **Rollback**: Revert all services with single change
- **Multi-region**: Different configs per region as needed

**The Channel System enables**:
- Fast, safe configuration updates
- Controlled, tested rollouts
- Quick rollback capabilities
- Consistent configuration management at scale

This is how channels work in practice - providing a powerful, flexible mechanism for managing configuration versions across hundreds of services.

