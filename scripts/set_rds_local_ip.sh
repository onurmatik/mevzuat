#!/usr/bin/env bash

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

set -euo pipefail

# ==== EDIT THESE ====
SG_ID="sg-0ebce90142a6b548a"
REGION="us-east-1"
DESCRIPTION="Local IP Access"
PROTOCOL="tcp"
PORT=5432              # 5432=Postgres, 3306=MySQL
# =====================

# 1) Current public IP
MY_IP="$(curl -s https://checkip.amazonaws.com)/32"
echo "My IP: $MY_IP"

# 2) Fetch current rules
RULES_JSON="$(aws ec2 describe-security-groups --group-ids "$SG_ID" --region "$REGION")"

# 3) Find & revoke rules that match our description + protocol + port
#    (Important: also pass protocol/port to revoke)
echo "$RULES_JSON" | jq -r \
  --arg PORT "$PORT" \
  --arg DESC "$DESCRIPTION" \
  --arg PROTOCOL "$PROTOCOL" \
  '.SecurityGroups[0].IpPermissions[]
   | select(.IpProtocol == $PROTOCOL)
   | select(.FromPort == ($PORT|tonumber) and .ToPort == ($PORT|tonumber))
   | .IpRanges[]
   | select(.Description == $DESC)
   | .CidrIp' | while read -r CIDR; do
      echo "Revoking old rule: $CIDR"
      aws ec2 revoke-security-group-ingress \
        --group-id "$SG_ID" \
        --region "$REGION" \
        --protocol "$PROTOCOL" \
        --port "$PORT" \
        --cidr "$CIDR"
done

# 4) Add the new IP with description (ip-permissions allows setting Description)
ADD_JSON='{
  "IpPermissions": [
    {
      "IpProtocol": "'"$PROTOCOL"'",
      "FromPort": '"$PORT"',
      "ToPort": '"$PORT"',
      "IpRanges": [
        { "CidrIp": "'"$MY_IP"'", "Description": "'"$DESCRIPTION"'" }
      ]
    }
  ]
}'

echo "Authorizing $MY_IP with description '$DESCRIPTION'..."
aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --region "$REGION" \
  --cli-input-json "$ADD_JSON"

echo "Done. Current IP set: $MY_IP"
