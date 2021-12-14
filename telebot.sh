# submit job as jobname userid job

JOBNAME=$1
USERID=$2
job=$3



# get job id, and return it to the server
jobID=$(python client.py $JOBNAME $USERID "start"  >&1)
# if response is 200 only then start the job


if [[ $? -eq 0 ]]; then  # information registered in database and message sent to user
$job                      # run the job
else
exit
fi


if [[ $? -eq 0 ]]; then
status='complete'
else
status='failed'
fi

python client.py $JOBNAME $USERID $status $jobID
