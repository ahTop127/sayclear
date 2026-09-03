#!/bin/zsh
cd "$(dirname "$0")"
export PATH="/opt/anaconda3/bin:$PATH"
exec /opt/anaconda3/bin/python3 -u -m sayclear
