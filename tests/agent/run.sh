#!/usr/bin/env bash
# Agent-test runner. Invokes the agent-driven skills against fixture
# inputs and compares outputs to stored expectations.
#
# Agent tests are gated separately from unit tests because they:
#   - invoke Claude Code non-interactively (costs API calls)
#   - have non-deterministic LLM output (allow retries, tolerate semantic diffs)
#   - rely on fixture directories under tests/agent/fixtures/
#
# Usage: ./tests/agent/run.sh [fixture-subset]

set -euo pipefail

FIXTURE_DIR="tests/agent/fixtures"

if [ ! -d "$FIXTURE_DIR" ] || [ -z "$(ls -A "$FIXTURE_DIR" 2>/dev/null)" ]; then
  echo "agent tests: no fixtures yet (fixtures land with Steps 8–11)"
  exit 0
fi

echo "agent tests: fixture runner not yet implemented"
echo "  TODO: invoke Claude Code headless, diff outputs, report pass/fail"
exit 0
