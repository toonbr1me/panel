#!/bin/bash
set -e

python -m alembic upgrade head
python main.py