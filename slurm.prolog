#!/bin/sh

# Script to run all scripts in a directory SCRIPTS_DIR.

function executeScripts {

        if [[ ! -d $SCRIPTS_DIR ]]; then
                exit 0
        fi

        IFS=$'\x0A'
        env | xargs sh -c export {} > /dev/null
        for SCRIPT in `ls $SCRIPTS_DIR`; do
                if [[ ! -x $SCRIPTS_DIR/$SCRIPT ]]; then
                        echo "File not marked as executable: $SCRIPTS_DIR/$SCRIPT"
                        exit 102
                fi

                $SCRIPTS_DIR/$SCRIPT $@
                EXIT_CODE=$?

                if [ "$EXIT_CODE" != "0" ]; then
                        exit $EXIT_CODE
                fi
        done

}

SCRIPTS_DIR="/sched/slurm-postjob/Epilog"

executeScripts

exit 0
