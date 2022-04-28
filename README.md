## Prolog & epilog

Prolog & Epilog for node clean-up and eviction catching. 

`slurm.epilog` and `slurm.prolog` call all scripts in the directory `$SCRIPTS_DIR` (which is defined inside the scripts).

The slurm.conf should be edited to call slurm.epilog & slurm.prolog 
where you put them on the system: i.e.

```
Prolog=/sched/slurm.prolog
Epilog=/sched/slurm.prolog
```

in `/etc/slurm/slurm.conf`

slurm.prolog & slurm.epilog need to be edited so that `$SCRIPTS_DIR` points to the paths for `slurm-postjob` and `slurm-prejob`, and all of the scripts need to be made executable. 

## Eviction catching

The `catch-eviction.py` prolog script sets a daemon running that monitors for evictions and writes to 
the job stderr when an eviction is caught. It also sends a sigterm to the job, and writes the eviction event to a table in the slurmdb. 

That table in the slurmdb needs to be set-up for this to work - the script `setup_eviction_table_in_db.py` can be run once and should do this for you.

You will need to insert the correct authentication information in `get_db_connection()` in both 
`setup_eviction_table_in_db.py` and `catch-eviction.py`.
