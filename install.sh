#!/bin/sh
# Retired installer entrypoint. Deliberately no environment override or upstream fallback.
# See DISTRIBUTION.md in bradvin/freedom-network for the source-only policy.
printf '%s\n' 'Freedom Network: scripted installation is disabled; use a reviewed source revision (see DISTRIBUTION.md).' >&2
exit 1