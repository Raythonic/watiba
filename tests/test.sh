#!/bin/bash
set -euo pipefail

project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
python=/home/rwalk/rwalkvenv3.12/bin/python

cd "$project_dir"
"$python" -W error -m unittest discover -s tests -p 'test_*.py' -v
