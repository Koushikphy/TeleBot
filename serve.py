import os
import re
import sys
import json
import logging
import threading
from operator import itemgetter
from sqlite3 import connect as sqlConnect
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot



class MyServer(BaseHTTPRequestHandler):
    def _set_headers(self, code=200):
        self.send_response(code)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            userId = int(data.get("id"))
            status = data.get("status")
            job    = data.get("job")
            host   = data.get("host")

            if db.checkIfRegisteredID(userId):
                if(status=='S'):  # newly submitted job
                    jobID = db.addJob(userId, host, job)
                    self._set_headers()
                    self.wfile.write(str(jobID).encode())

                    logger.info(f'New job added for user {userId} at {host} : {job}')
                    bot.send_message(userId, f'A new job <i>{job}</i> is submitted on <b>{host}</b>')

                else:
                    jobID = data.get("jobID")  # if not starting, request must contain a job ID

                    db.closeJob(jobID, status)  # jobID is primary key so no other info is required
                    txt = 'is now complete.' if status=='C' else 'has failed.'
                    logger.info(f'Job closed for user {userId} at {host} : {job}, job={job}, jobID={jobID}')
                    bot.send_message(userId, f'Your job <i>{job}</i> on <b>{host}</b>  {txt}')
                    self._set_headers()
            else:
                logger.info(f"Incoming request for unregistered user: {userId}")
                self._set_headers(503)
        except Exception as e:
            logger.exception()
            print('failed', e)
            self._set_headers(500)


def runServer(addr='0.0.0.0',port=8123):
    server_address = (addr, port)
    httpd = HTTPServer(server_address, MyServer)
    print(f"Starting httpd server on {addr}:{port}")
    httpd.serve_forever()


class MyFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt="%I:%M:%S %p %d-%m-%Y"):
        logging.Formatter.__init__(self, fmt, datefmt)

    def format(self, record):
        self._style._fmt = "[%(asctime)s] - %(message)s"
        result = logging.Formatter.format(self, record)
        return result


def makeLogger(logFile, stdout=True):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = MyFormatter()
    fh = logging.FileHandler(logFile)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    if stdout:
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger



class DataBase:
    def __init__(self, dbFile):
        self.dbFile = dbFile
        if not os.path.exists(dbFile): # create the database
            with sqlConnect(self.dbFile) as con:
                cur = con.cursor()
                cur.executescript( "CREATE TABLE JOBINFO("
                "jobID integer NOT NULL PRIMARY KEY AUTOINCREMENT,"
                "userId INTEGER NOT NULL,"
                "host TEXT NOT NULL,"
                "status TEXT NOT NULL,"
                "job TEXT NOT NULL);"
                "CREATE TABLE USERIDS ( userid NOT NULL UNIQUE);")


    def listRunningJobs(self,userID):
        # print(userID, type(userID))
        with sqlConnect(self.dbFile) as con:
            cur = con.cursor()
            cur.execute('Select host,job from JOBINFO where userId=? and status="R"',(userID,))
            data = cur.fetchall()
            count = len(data)
        if count:
            data = [[f'{l}. {i}',j] for l,(i,j) in enumerate(data, start=1)]
            data = [[trimMe(i) for i in j ] for j in data]
            lens = [max([len(i)+1 for i in a]) for a in list(zip(*data))]
            txt = [[i.ljust(lens[k]) for k,i in enumerate(j)] for j in data]
            header = '  '.join(['Host'.center(lens[0]), "Job".center(lens[1])])
            txt = "The follwing jobs are running:\n\n <pre>" +header+\
                '\n'+'-'*30+'\n'+'\n'.join(['  '.join(i) for i in txt])+'</pre>'
        else:
            txt = "No running jobs found"
        return txt,count

    def listAllJobs(self,userID):
        with sqlConnect(self.dbFile) as con:
            cur = con.cursor()
            cur.execute('Select host,status,job from JOBINFO where userId=?',(userID,))
            data = cur.fetchall()
            count = len(data)
        if count:
            data = [[f'{l}. {i}',j,k] for l,(i,j,k) in enumerate(data, start=1)]
            data = [[trimMe(i) for i in j ] for j in data]
            lens = [max([len(i)+1 for i in a]) for a in list(zip(*data))]
            txt = [[i.ljust(lens[k]) for k,i in enumerate(j)] for j in data]
            header = '  '.join(['Host'.center(lens[0]),"S".center(lens[1]) , "Job".center(lens[2])])
            txt = "List of Jobs:\n\n <pre>" +header+\
                '\n'+'-'*30+'\n'+'\n'.join(['  '.join(i) for i in txt])+'</pre>'
        else:
            txt = "Job List empty"
        return txt,count


    def addJob(self,userId, host, job):
        # return the add code
        with sqlConnect(self.dbFile) as con:
            cur = con.cursor()
            cur.execute('Insert into JOBINFO (userId, host, status, job) values (?,?,?,?)',(userId,host,'R',job))
            cur.execute("select seq from sqlite_sequence where name='JOBINFO'") # as it is primary key
            jobID, = cur.fetchall()[0]
            return jobID


    def closeJob(self,jobID, status):
        with sqlConnect(self.dbFile) as con:
            cur = con.cursor()
            cur.execute("UPDATE JOBINFO SET status=? where jobID=?",(status,jobID))


    def removeJob(self, userId, index):
        with sqlConnect(self.dbFile) as con:
            cur = con.cursor()
            cur.execute('Select jobID from JOBINFO where userId=?',(userId,))
            jobIds = cur.fetchall()
            jobIdsToRemove= [jobIds[i-1] for i in index]
            cur.executemany("Delete from JOBINFO where jobID=? ",jobIdsToRemove)
            logger.info(f'Job(s) removed for user {userId} jobIDs : {" ".join([str(i) for (i,) in jobIdsToRemove])}')


    def checkIfRegisteredID(self,userID):
        with sqlConnect(self.dbFile) as con:
            cur = con.cursor()
            cur.execute('SELECT userid from USERIDS')
            userids = [i for (i,) in cur.fetchall()]
            return userID in userids


    def checkIfRegisteredUser(self,user):
        if self.checkIfRegisteredID(user.id):
            return True
        else:
            logger.info(f"Incoming request for unregistered user: {user.first_name} {user.last_name} ({user.id})")
            bot.send_message(ADMIN, f'Registration requested for {user.first_name} {user.last_name} ({user.id})')
            return False


    def registerUser(self, userid):
        with sqlConnect(self.dbFile) as con:
            cur = con.cursor()
            cur.execute('INSERT into USERIDS (userid) values (?)',(userid,))
            bot.send_message(ADMIN, f'{userid} added.')
            bot.send_message(userid, 'You are succesfully registered with the bot to submit jobs.')


logger = makeLogger('stat.log')
db = DataBase('sqlite3.db')


with open('.key') as f:
    # file written as <bot_API_key> <my_key>
    myKey,ADMIN = f.read().strip().split()
    bot= telebot.TeleBot(myKey, parse_mode='HTML')



@bot.message_handler(commands='start')
def send_welcome(message):
    user = message.from_user
    bot.send_message(user.id, f"Hi there {user.first_name} {user.last_name}. "
        "Welcome to this automated bot. This bot keeps track of your running jobs"
        "and send you notification when your job is complete or failed."
        f"Your id is <b>{user.id}</b>. Use this when submitting jobs")
    if not db.checkIfRegisteredUser(user):
        bot.send_message(user.id,"Note: You are not signed up for registering job with the bot"
        "Please wait for the admin to accept your request.")


@bot.message_handler(commands='listjobs')
def send_listRunningJobs(message):
    user = message.from_user
    logger.info(f'List of running jobs requested for user={user.id}')
    if db.checkIfRegisteredUser(user):
        jobs,_ = db.listRunningJobs(user.id)
        bot.send_message(user.id,jobs)



@bot.message_handler(commands='listalljobs')
def send_listAllJobs(message):
    user = message.from_user
    logger.info(f'List of all jobs requested for user={user.id}')
    if db.checkIfRegisteredUser(user):
        jobs,_ = db.listAllJobs(user.id)
        bot.send_message(user.id,jobs)



@bot.message_handler(commands='myinfo')
def send_userinfo(message):
    user = message.from_user
    logger.info(f'Information requested for {user.first_name} {user.last_name} ({user.id})')
    bot.send_message(user.id, f"Hi there {user.first_name} {user.last_name}. "
        f"Your id is <b>{user.id}</b>. Use this when submitting jobs")


@bot.message_handler(commands='remove')
def start(message):
    logger.info(f'Requested to remove jobs for user={message.from_user.id}')
    txt, count = db.listAllJobs(message.from_user.id)
    sent = bot.send_message(message.from_user.id, 'Provide serial number of jobs to remove.\n'+txt)
    if count : bot.register_next_step_handler(sent, removewithIDs)


def removewithIDs(message):
    toRemoveIds = [int(i) for i in re.split('[, ]+',message.text)]
    db.removeJob(message.from_user.id,toRemoveIds)
    bot.send_message(message.from_user.id, f'These jobs are removed {",".join([str(i) for i in toRemoveIds])}')



def trimMe(myStr):
    return myStr[:10]+'...' if len(myStr)>13 else myStr


threading.Thread(target=bot.polling,daemon=True).start()
runServer()