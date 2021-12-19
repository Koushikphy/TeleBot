#!/bin/bash
# submit job as jobname userid job, using shell script, as I don't want to run the job from another python, just.

#TODO: Accept command and job name with multiple names without a quote

# URL of the bot server
URL="http://192.168.31.11:8123"
usage="
Run this script as:

  telebot -u USER_ID -n JOB_Name -j JOB_Command

"

while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    -h) echo "$usage"; exit 1;;
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
      *) echo "Improper usage"; echo "$usage";  exit 1;;
  esac
done



if [ -z $USERID ]; then
    echo "Missing User ID (-u)"
    echo "$usage"
    exit 1
fi
if [ -z "$JOBNAME" ]; then
    echo "Missing Job Name (-n)"
    echo "$usage"
    exit 1
fi
if [ -z "$job" ]; then
    echo "Missing Job command (-j)"
    echo "$usage"
    exit 1
fi



# register the job to the bot server database, it should return a status code and a job ID if successfully added
out=$(curl -s -H "Content-Type:application/json" ${URL} -w "%{http_code}" --noproxy '*' -d "$(cat <<EOF
{"id":"${USERID}",
"host":"$(hostname)",
"job":"${JOBNAME}",
"status":"S"}
EOF
)")


jobID=${out:0:${#out}-3}        # job id
stat=${out:${#out}-3:${#out}}   # server response



if [ $stat == 200 ]; then
    # successfully regiester now submit the job
    $job
elif [ $stat == 503 ]; then
    echo "User ID not registered to submit jobs. Contact the admin."
    exit
elif [ $stat == 000 ]; then
    echo "Can not contact the bot. Make sure the bot server is running."
    exit
else
    echo "Something went wrong on the server side. Contact the admin."
    exit
fi



if [[ $? -eq 0 ]]; then
    status="C"
else
    status="F"
fi

out=$(curl -s -H "Content-Type:application/json" ${URL} -w "%{http_code}" --noproxy '*' -d "$(cat <<EOF
{"id":"${USERID}",
"host":"$(hostname -f)",
"job":"${JOBNAME}",
"status":"${status}",
"jobID":"${jobID}"}
EOF
)"
)