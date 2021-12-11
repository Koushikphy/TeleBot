import sys,requests,json
import socket

# print (sys.argv)
jobName = sys.argv[1]
userID = sys.argv[2]
status = sys.argv[3]
host = socket.gethostname()

print(jobName, userID, status, host)
req = requests.post(
    'http://localhost:8080',
    json.dumps({
        'id':userID,
        'host':host,
        'job':jobName,
        'status':status
        })
    )
print(req)

if req.status_code!=200:
    print('Something went wrong could not register the job')
    sys.exit(1)
