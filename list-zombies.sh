ps -ww -eo user:32,pid,ppid,stat,args | awk 'NR == 1 || $4 ~ /^Z/'
