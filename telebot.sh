# submit job as jobname userid job

JOBNAME=$1
USERID=$2
job=$3
python client.py $JOBNAME $USERID "start"
# if  response is 200 only then start the job
#$3
echo $?
#python client.py $JOBNAME $USERID "complete"
