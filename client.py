import sys,requests,json
import socket

jobName = sys.argv[1]
userID = sys.argv[2]
status = sys.argv[3]
jobID   = sys.argv[4] if len(sys.argv)==5 else None

host = socket.gethostname()

# print(jobName, userID, status, host)
req = requests.post(
    'http://localhost:8123',   #<---- change this
    json.dumps({
        'id':userID,
        'host':host,
        'job':jobName,
        'status':status,
        'jobID': jobID
        })
    )


if req.status_code!=200:
    if req.status_code==503:
        sys.stderr.write('User not registered\n')
    else:
        sys.stderr.write('Something went wrong could not register the job\n')
    sys.exit(1)
else:
    if len(sys.argv)!=5: # pass the job id to the shell
        print(req.content.decode())
