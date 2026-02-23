#!/bin/bash
# =============================================================================
# FlowyML GCP Cost Audit
# =============================================================================
# Generates a comprehensive cost audit report that can be shared with AI
# for optimization recommendations.
#
# Usage: make cost-audit
# =============================================================================

set -euo pipefail

PROJECT="${GCP_PROJECT:-}"
REGION="${GCP_REGION:-europe-west1}"
SERVICE="${GCP_SERVICE:-flowyml}"

if [ -z "$PROJECT" ]; then
  echo "❌ GCP_PROJECT not set. Run: make cost-audit"
  exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║              💰 FLOWYML GCP COST AUDIT REPORT                       ║"
echo "║              $(date '+%Y-%m-%d %H:%M:%S %Z')                             ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════════════"
echo "1. PROJECT & BILLING INFO"
echo "═══════════════════════════════════════════════════════════════════════"
echo "Project ID:    $PROJECT"
echo "Region:        $REGION"
BILLING=$(gcloud billing projects describe "$PROJECT" --format='value(billingAccountName)' 2>/dev/null || echo "unknown")
echo "Billing Acct:  $BILLING"
echo ""
echo "Enabled APIs (potentially billable):"
gcloud services list --enabled --project="$PROJECT" \
  --format='table(config.name)' 2>/dev/null | grep -E '(run|sql|compute|redis|secret|artifact|monitoring|logging|build|aiplatform|storage)' | while read api; do
  echo "  • $api"
done
echo ""

# ─────────────────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════════════"
echo "2. CLOUD RUN SERVICES"
echo "═══════════════════════════════════════════════════════════════════════"
gcloud run services list --project="$PROJECT" --region="$REGION" \
  --format='table(metadata.name,status.url)' 2>/dev/null || echo "No services found"
echo ""

for svc in $(gcloud run services list --project="$PROJECT" --region="$REGION" --format='value(metadata.name)' 2>/dev/null); do
  echo "--- Service: $svc ---"
  MIN=$(gcloud run services describe "$svc" --project="$PROJECT" --region="$REGION" \
    --format='value(spec.template.metadata.annotations["autoscaling.knative.dev/minScale"])' 2>/dev/null || echo "0")
  MAX=$(gcloud run services describe "$svc" --project="$PROJECT" --region="$REGION" \
    --format='value(spec.template.metadata.annotations["autoscaling.knative.dev/maxScale"])' 2>/dev/null || echo "?")
  CPU=$(gcloud run services describe "$svc" --project="$PROJECT" --region="$REGION" \
    --format='value(spec.template.spec.containers[0].resources.limits.cpu)' 2>/dev/null || echo "?")
  MEM=$(gcloud run services describe "$svc" --project="$PROJECT" --region="$REGION" \
    --format='value(spec.template.spec.containers[0].resources.limits.memory)' 2>/dev/null || echo "?")
  IDLE=$(gcloud run services describe "$svc" --project="$PROJECT" --region="$REGION" \
    --format='value(spec.template.metadata.annotations["run.googleapis.com/cpu-throttling"])' 2>/dev/null || echo "?")
  BOOST=$(gcloud run services describe "$svc" --project="$PROJECT" --region="$REGION" \
    --format='value(spec.template.metadata.annotations["run.googleapis.com/startup-cpu-boost"])' 2>/dev/null || echo "?")
  echo "  Min/Max instances: ${MIN:-0} / ${MAX:-?}"
  echo "  CPU / Memory:      $CPU / $MEM"
  echo "  CPU idle:          $IDLE"
  echo "  Startup boost:     $BOOST"
  if [ "${MIN:-0}" = "0" ] || [ -z "$MIN" ]; then
    echo "  💰 Cost: ~€0-5/mo (scale-to-zero)"
  else
    echo "  ⚠️  Cost: ~€50-80/mo (always warm!)"
  fi
  echo ""
done

# ─────────────────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════════════"
echo "3. CLOUD SQL INSTANCES"
echo "═══════════════════════════════════════════════════════════════════════"
for db in $(gcloud sql instances list --project="$PROJECT" --format='value(name)' 2>/dev/null); do
  echo "--- Instance: $db ---"
  TIER=$(gcloud sql instances describe "$db" --project="$PROJECT" --format='value(settings.tier)' 2>/dev/null || echo "?")
  STATE=$(gcloud sql instances describe "$db" --project="$PROJECT" --format='value(state)' 2>/dev/null || echo "?")
  ACTIVATION=$(gcloud sql instances describe "$db" --project="$PROJECT" --format='value(settings.activationPolicy)' 2>/dev/null || echo "?")
  STORAGE=$(gcloud sql instances describe "$db" --project="$PROJECT" --format='value(settings.dataDiskSizeGb)' 2>/dev/null || echo "?")
  echo "  Tier: $TIER | State: $STATE | Policy: $ACTIVATION | Storage: ${STORAGE}GB"
  case "$TIER" in
    db-f1-micro) echo "  💰 Cost: ~€7/mo (always-on)" ;;
    db-g1-small) echo "  💰 Cost: ~€25/mo" ;;
    *) echo "  💰 Cost: varies by tier" ;;
  esac
  echo ""
done

# ─────────────────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════════════"
echo "4. COMPUTE ENGINE (VMs, VPC Connectors)"
echo "═══════════════════════════════════════════════════════════════════════"
echo "VMs:"
gcloud compute instances list --project="$PROJECT" \
  --format='table(name,zone,machineType.basename(),status)' 2>/dev/null || echo "  None"
echo ""
echo "VPC Access Connectors (€6-7/mo each!):"
gcloud compute networks vpc-access connectors list --project="$PROJECT" --region="$REGION" \
  --format='table(name,state,machineType,minInstances,maxInstances)' 2>/dev/null || echo "  None (good)"
echo ""
echo "MIGs:"
gcloud compute instance-groups managed list --project="$PROJECT" \
  --format='table(name,zone,targetSize)' 2>/dev/null || echo "  None"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════════════"
echo "5. NETWORKING"
echo "═══════════════════════════════════════════════════════════════════════"
echo "Static External IPs (€2.88/mo each if unused!):"
gcloud compute addresses list --project="$PROJECT" \
  --format='table(name,region,address,status)' 2>/dev/null || echo "  None"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════════════"
echo "6. SECRETS & REGISTRY"
echo "═══════════════════════════════════════════════════════════════════════"
SECRET_COUNT=$(gcloud secrets list --project="$PROJECT" --format='value(name)' 2>/dev/null | wc -l | tr -d ' ')
echo "Secrets: $SECRET_COUNT (~€0.06/secret/mo)"
echo ""
echo "Artifact Registry:"
gcloud artifacts repositories list --project="$PROJECT" --location="$REGION" \
  --format='table(name,format,sizeBytes)' 2>/dev/null || echo "  None"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════════════"
echo "7. TRAFFIC ANALYSIS (Last 14 Days)"
echo "═══════════════════════════════════════════════════════════════════════"
SINCE=$(date -v-14d '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -d '14 days ago' '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null)

echo "Request count per service:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND timestamp>=\"$SINCE\"" \
  --project="$PROJECT" --limit=1000 \
  --format='value(resource.labels.service_name)' 2>/dev/null | sort | uniq -c | sort -rn || echo "  No data"
echo ""

echo "Top 15 Paths:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND timestamp>=\"$SINCE\"" \
  --project="$PROJECT" --limit=1000 \
  --format='value(httpRequest.requestUrl)' 2>/dev/null | sort | uniq -c | sort -rn | head -15 || echo "  No data"
echo ""

echo "Top 10 Caller IPs:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND timestamp>=\"$SINCE\"" \
  --project="$PROJECT" --limit=1000 \
  --format='value(httpRequest.remoteIp)' 2>/dev/null | sort | uniq -c | sort -rn | head -10 || echo "  No data"
echo ""

echo "HTTP Status Codes:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND timestamp>=\"$SINCE\"" \
  --project="$PROJECT" --limit=1000 \
  --format='value(httpRequest.status)' 2>/dev/null | sort | uniq -c | sort -rn || echo "  No data"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════════════"
echo "8. MONITORING & ALERTS"
echo "═══════════════════════════════════════════════════════════════════════"
echo "Alert Policies:"
gcloud alpha monitoring policies list --project="$PROJECT" \
  --format='table(displayName,enabled)' 2>/dev/null || echo "  None configured"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════════════"
echo "9. COST OPTIMIZATION CHECKLIST"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "  [ ] Cloud Run min-instances = 0 (scale to zero)"
echo "  [ ] Cloud Run cpu_idle = true"
echo "  [ ] Cloud Run startup_cpu_boost = true"
echo "  [ ] Cloud Run memory right-sized"
echo "  [ ] Cloud SQL tier right-sized (db-f1-micro = €7/mo)"
echo "  [ ] Cloud SQL stopped if unused (activation-policy=NEVER)"
echo "  [ ] No VPC Access Connectors (use Direct VPC Egress)"
echo "  [ ] No unused static IPs"
echo "  [ ] Budget alerts configured"
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "END OF AUDIT — $(date '+%Y-%m-%d %H:%M:%S') — Project: $PROJECT"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "💡 TIP: Copy output → make cost-audit 2>&1 | pbcopy"
echo ""
