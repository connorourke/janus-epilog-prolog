#!/bin/bash
# REmove temp files

find /tmp/ -maxdepth 1 -user $SLURM_JOB_UID | while read I; do

rm -rf $I > /dev/null 2 > /dev/null

done
