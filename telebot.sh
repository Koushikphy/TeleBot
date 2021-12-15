# submit job as jobname userid job, using shell script, as I don't want to run the job from another python, just.

#TODO: Accept command and job name with multiple names without a quote

while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    -h) echo "Run this script as:
    
    telebot -u USER_ID -n JOB_Name -j JOB_Command
    
    "; exit 1;;
    -u) # user id
      USERID="$2"
      shift # past argument
      shift # past value
      ;;
    -n) # name of job
      JOBNAME="$2"
      shift # past argument
      shift # past value
      ;;
    -j) # job
      job="$2"
      shift # past argument
      shift # past value
      ;;
      *) echo "Improper usage"; exit 1;;
  esac
done


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
