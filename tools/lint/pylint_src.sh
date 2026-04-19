#!/usr/bin/env bash
set -euo pipefail

collect_python_files() {
  local root="$1"
  if [ ! -d "$root" ]; then
    return
  fi

  if command -v rg >/dev/null 2>&1; then
    rg --files "$root" -g '*.py'
  else
    find "$root" -name '*.py' -print | sed 's#^\./##'
  fi
}

declare -a py_files=()

if [ "$#" -gt 0 ]; then
  for path in "$@"; do
    if [[ "$path" == src/* ]]; then
      py_files+=("$path")
    fi
  done
else
  while IFS= read -r path; do
    py_files+=("$path")
  done < <(collect_python_files "src")
fi

if [ "${#py_files[@]}" -eq 0 ]; then
  echo "No target files to lint: exiting."
  exit 0
fi

python -m pylint "${py_files[@]}" \
  --disable=all \
  --enable=missing-module-docstring,missing-class-docstring,missing-function-docstring,invalid-name
