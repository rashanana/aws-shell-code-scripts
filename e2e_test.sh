#!/bin/bash

# Load env vars
if [ -f .env ]; then
  export $(cat .env | xargs)
else
  echo "ERROR: .env file not found"
  exit 1
fi

CORRELATION_ID="e2e-test-$(date +%s)"

echo "=============================="
echo "Starting E2E Test"
echo "Correlation ID: $CORRELATION_ID"
echo "=============================="

EXECUTION_ARN=$(aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --input "{\"correlationId\": \"$CORRELATION_ID\"}" \
  --query executionArn \
  --output text)

echo "Execution ARN: $EXECUTION_ARN"

START_TIME=$(aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN \
  --query startDate \
  --output text)

START_MS=$(date -d "$START_TIME" +%s%3N)
echo "Execution started: $START_TIME"

echo ""
echo "Polling for completion..."
while true; do
  STATUS=$(aws stepfunctions describe-execution \
    --execution-arn $EXECUTION_ARN \
    --query status \
    --output text)
  echo "$(date '+%H:%M:%S') Status: $STATUS"
  if [ "$STATUS" != "RUNNING" ]; then
    break
  fi
  sleep 10
done

echo ""
echo "=============================="
echo "FINAL STATUS: $STATUS"
echo "=============================="

echo ""
echo "=== EXECUTION RESULT ==="
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN \
  --query '{status: status, start: startDate, stop: stopDate, output: output}' \
  --output table

echo ""
echo "=== LAMBDA 1 LOGS ==="
aws logs filter-log-events \
  --log-group-name $LAMBDA_1 \
  --start-time $START_MS \
  --query 'events[].message' \
  --output text

echo ""
echo "=== LAMBDA 2 LOGS ==="
aws logs filter-log-events \
  --log-group-name $LAMBDA_2 \
  --start-time $START_MS \
  --query 'events[].message' \
  --output text

echo ""
echo "=== LAMBDA 3 LOGS ==="
aws logs filter-log-events \
  --log-group-name $LAMBDA_3 \
  --start-time $START_MS \
  --query 'events[].message' \
  --output text

echo ""
echo "=============================="
echo "E2E Test Complete"
echo "=============================="
