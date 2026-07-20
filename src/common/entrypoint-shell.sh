#!/bin/sh
if [ $# -gt 0 ] && [ "$1" = "${1#-}" ]; then
	exec "$@"
else
	exec "${SHELL:-/bin/sh}" "$@"
fi
