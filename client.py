import sys,requests,json
import socket

# print (sys.argv)
jobName = sys.argv[1]
userID = sys.argv[2]
status = sys.argv[3]
jobID   = sys.argv[4] if len(sys.argv)==5 else None

host = socket.gethostname()

# print(jobName, userID, status, host)
req = requests.post(
    'http://192.168.31.88:8080',
    json.dumps({
        'id':userID,
        'host':host,
        'job':jobName,
        'status':status,
        'jobID': jobID
        })
    )


if req.status_code!=200:
    print('Something went wrong could not register the job')
    print(req.status_code)
    print(req.content)
    sys.exit(1)
else:
    if len(sys.argv)!=5:
        print(req.content.decode())
