#!/bin/bash
#
# This script will kill any user processes on a node when the last
# SLURM job there ends. For example, if a user directly logs into
# an allocated node SLURM will not kill that process without this
# script being executed as an epilog.
#

if [ x$SLURM_JOB_UID = "x" ] ; then
        exit 0
fi

if [ x$SLURM_JOB_ID = "x" ] ; then
        exit 0
fi

#
# Don't try to kill user root or system daemon jobs
#
if [ $SLURM_JOB_UID -lt 100 ] ; then
        exit 0
fi

job_list=`squeue --noheader --format=%A --user=$SLURM_JOB_USER --node=localhost`

#echo $job_list 

for job_id in $job_list
do
        if [ $job_id -ne $SLURM_JOB_ID ] ; then
                exit 0
        fi
done
#
# No other SLURM jobs, purge all remaining processes of this user
#
pkill -KILL -U $SLURM_JOB_UID


#if [[ $SLURM_JOB_USER == *sac* ]] || [[ $SLURM_JOB_USER == *mjc03* ]]; then
#	/cm/shared/apps/slurm/bath/scripts/clean-up-user-files.pl
#fi



exit 0
