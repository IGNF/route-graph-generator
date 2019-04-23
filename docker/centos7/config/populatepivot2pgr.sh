#!/usr/bin/env sh

R2GG_ARG=$1

r2gg:populate_pivot ${R2GG_ARG}
r2gg:pivot2pgrouting ${R2GG_ARG}
