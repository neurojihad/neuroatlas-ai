#!/usr/bin/env bash
# Thin wrapper around the Atlassian Cloud REST API for NeuroAtlas Jira ops.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${REPO_ROOT}/infra/.env"

load_env() {
  if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source <(grep -v '^\s*#' "${ENV_FILE}" | grep -v '^\s*$' | sed 's/\r$//')
    set +a
  fi
}

require_vars() {
  JIRA_BASE_URL="${JIRA_BASE_URL:-https://neurojihad.atlassian.net}"
  JIRA_BASE_URL="${JIRA_BASE_URL%/}"
  JIRA_PROJECT_KEY="${JIRA_PROJECT_KEY:-NLS}"
  if [[ -z "${JIRA_EMAIL:-}" || -z "${JIRA_API_TOKEN:-}" ]]; then
    echo "Set JIRA_EMAIL and JIRA_API_TOKEN in infra/.env (see infra/.env.example)." >&2
    exit 1
  fi
}

auth_header() {
  printf '%s' "${JIRA_EMAIL}:${JIRA_API_TOKEN}" | base64 | tr -d '\n'
}

text_to_adf() {
  local text="${1:-}"
  local json='{"type":"doc","version":1,"content":['
  local first=1
  while IFS= read -r line || [[ -n "${line}" ]]; do
    line="${line//\\/\\\\}"
    line="${line//\"/\\\"}"
    if [[ ${first} -eq 0 ]]; then json+=','; fi
    first=0
    json+='{"type":"paragraph","content":[{"type":"text","text":"'"${line}"'"}]}'
  done <<< "${text}"
  if [[ ${first} -eq 1 ]]; then
    json+='{"type":"paragraph","content":[{"type":"text","text":""}]}'
  fi
  json+=']}'
  printf '%s' "${json}"
}

jira_request() {
  local method="$1"
  local path="$2"
  local body="${3:-}"
  local args=(-sS -X "${method}" -H "Authorization: Basic $(auth_header)" -H "Accept: application/json")
  if [[ -n "${body}" ]]; then
    args+=(-H "Content-Type: application/json" -d "${body}")
  fi
  curl "${args[@]}" "${JIRA_BASE_URL}${path}"
}

cmd="${1:-}"
shift || true

load_env
require_vars

case "${cmd}" in
  search)
    jql="${1:?Usage: jira_api.sh search \"project = NLS\"}"
    body=$(printf '{"jql":"%s","maxResults":50,"fields":["summary","status","issuetype","parent"]}' "${jql}")
    resp="$(jira_request POST "/rest/api/3/search/jql" "${body}")"
    echo "${resp}" | python -c "
import json, sys
data = json.load(sys.stdin)
issues = data.get('issues') or []
if not issues:
    print('(no issues)')
for i in issues:
    f = i.get('fields', {})
    print(f\"{i['key']}  [{f.get('status', {}).get('name', '?')}]  {f.get('summary', '')}\")
"
    ;;

  get)
    key="${1:?Usage: jira_api.sh get NLS-201}"
    jira_request GET "/rest/api/3/issue/${key}?fields=summary,status,description,issuetype,parent"
    echo
    ;;

  create)
    type="Story"
    summary=""
    epic=""
    description=""
    description_file=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --type) type="$2"; shift 2 ;;
        --summary) summary="$2"; shift 2 ;;
        --epic) epic="$2"; shift 2 ;;
        --description) description="$2"; shift 2 ;;
        --description-file) description_file="$2"; shift 2 ;;
        *) echo "Unknown arg: $1" >&2; exit 1 ;;
      esac
    done
    [[ -n "${summary}" ]] || { echo "Usage: jira_api.sh create --summary \"...\" [--type Story] [--epic NLS-EPIC-02]" >&2; exit 1; }
    if [[ -n "${description_file}" ]]; then
      description="$(cat "${description_file}")"
    fi
    adf="$(text_to_adf "${description}")"
    if [[ -n "${epic}" ]]; then
      body=$(printf '{"fields":{"project":{"key":"%s"},"summary":"%s","description":%s,"issuetype":{"name":"%s"},"parent":{"key":"%s"}}}' \
        "${JIRA_PROJECT_KEY}" "${summary}" "${adf}" "${type}" "${epic}")
    else
      body=$(printf '{"fields":{"project":{"key":"%s"},"summary":"%s","description":%s,"issuetype":{"name":"%s"}}}' \
        "${JIRA_PROJECT_KEY}" "${summary}" "${adf}" "${type}")
    fi
    resp="$(jira_request POST "/rest/api/3/issue" "${body}")"
    key="$(echo "${resp}" | python -c "import json,sys; print(json.load(sys.stdin)['key'])")"
    echo "Created: ${key}"
    echo "URL:     ${JIRA_BASE_URL}/browse/${key}"
    ;;

  transitions)
    key="${1:?Usage: jira_api.sh transitions NLS-201}"
    jira_request GET "/rest/api/3/issue/${key}/transitions"
    echo
    ;;

  comment)
    key="${1:?Usage: jira_api.sh comment NLS-201 --description \"...\"}"
    shift
    description=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --description) description="$2"; shift 2 ;;
        *) echo "Unknown arg: $1" >&2; exit 1 ;;
      esac
    done
    [[ -n "${description}" ]] || { echo "Provide --description" >&2; exit 1; }
    adf="$(text_to_adf "${description}")"
    body=$(printf '{"body":%s}' "${adf}")
    jira_request POST "/rest/api/3/issue/${key}/comment" "${body}" >/dev/null
    echo "Comment added to ${key}"
    ;;

  boards)
    jira_request GET "/rest/agile/1.0/board?projectKeyOrId=${JIRA_PROJECT_KEY}"
    echo
    ;;

  sprints)
    board_id="${1:?Usage: jira_api.sh sprints <board_id>}"
    jira_request GET "/rest/agile/1.0/board/${board_id}/sprint"
    echo
    ;;

  *)
    echo "Unknown command '${cmd}'. Use: search, get, create, transitions, comment, boards, sprints" >&2
    exit 1
    ;;
esac
