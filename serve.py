import os
import re
import sys
import json
import logging
import threading
from sqlite3 import connect as sqlConnect
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot



# Logger--------------------------------------------

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



# Custom http server for tracing incoming connection from client----

class MyServer(BaseHTTPRequestHandler):
    def _set_headers(self, code=200):
        self.send_response(code)
        self.send_header("Content-type", "application/json")
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
            # job status used: C: Complete; F: Failed; R: Running
            if db.checkIfRegisteredID(userId):
                if(status=='S'):  # newly submitted job
                    jobID = db.addJob(userId, host, job)
                    self._set_headers()
                    self.wfile.write(str(jobID).encode())

                    logger.info(f'New job added for user {userId} at {host} : {job}')
                    bot.send_message(userId, f'A new job <i>{job}</i> is submitted on <b>{host}</b>')

                elif status in ["C","F"]: # check if already closed
                    jobID = data.get("jobID")  # if not starting, request must contain a job ID

                    db.closeJob(jobID, status)  # jobID is primary key so no other info is required
                    txt = 'is now complete.' if status=='C' else 'has failed.'
                    logger.info(f'Job closed for user {userId} at {host} : {job}, job={job}, jobID={jobID}')
                    bot.send_message(userId, f'Your job <i>{job}</i> on <b>{host}</b>  {txt}')
                    self._set_headers()
                else:
                    logger.info(f"Warning: Incoming unknows status: {status}. User ID={userId}, Host={host} Job={job}")
                    self._set_headers(503)
            else:
                logger.info(f"Incoming request for unregistered user: {userId}")
                self._set_headers(503)
        except Exception as e:
            logger.exception("Failed to parse request.")
            self._set_headers(500)


def runServer(addr='0.0.0.0',port=8123):
    server_address = (addr, port)
    # would fail if port is occupied
    httpd = HTTPServer(server_address, MyServer)
    print(f"Starting httpd server on {addr}:{port}")
    httpd.serve_forever()



# Database to keep track of all jobs for all users-----

class DataBase:
    def __init__(self, dbFile):
        self.dbFile = dbFile
        if not os.path.exists(dbFile): # create the database, if doesn't exist
            with sqlConnect(self.dbFile) as con:
                cur = con.cursor()
                cur.executescript( "CREATE TABLE JOBINFO("
                "jobID integer NOT NULL PRIMARY KEY AUTOINCREMENT,"
                "userId INTEGER NOT NULL,"
                "host TEXT NOT NULL,"
                "status TEXT NOT NULL,"
                "job TEXT NOT NULL);"
                "CREATE TABLE USERIDS ( userid NOT NULL UNIQUE);")
                # add the Admin ID to the database
                cur.execute('INSERT into USERIDS (userid) values (?)',(ADMIN,))


    def listRunningJobs(self, userID):
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
        # Adds new job to the database and returns the job ID
        with sqlConnect(self.dbFile) as con:
            cur = con.cursor()
            cur.execute('Insert into JOBINFO (userId, host, status, job) values (?,?,?,?)',(userId,host,'R',job))
            # jobID is a primary key in JOBINFO, so sqlite should keep that information in `sqlite_sequence` table
            cur.execute("select seq from sqlite_sequence where name='JOBINFO'") 
            jobID, = cur.fetchall()[0]
            return jobID


    def closeJob(self, jobID, status):
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


    def checkIfRegisteredID(self, userID):
        with sqlConnect(self.dbFile) as con:
            cur = con.cursor()
            cur.execute('SELECT userid from USERIDS')
            userids = [int(i) for (i,) in cur.fetchall()]
            return userID in userids


    def checkIfRegisteredUser(self, user):
        if self.checkIfRegisteredID(user.id):
            return True
        else:
            logger.info(f"Incoming request for unregistered user: {user.first_name} {user.last_name} ({user.id})")
            bot.send_message(ADMIN, f'Registration requested for {user.first_name} {user.last_name} ({user.id})')
            return False


    def registerUser(self, userID):
        with sqlConnect(self.dbFile) as con:
            cur = con.cursor()
            cur.execute('SELECT userid from USERIDS')
            userids = [i for (i,) in cur.fetchall()]
            if userID in userids:
                bot.send_message(ADMIN, f'User ID {userID} is already in database.')
                logger.info(f'User ID {userID} is already in database.')
            else:
                cur.execute('INSERT into USERIDS (userid) values (?)',(userID,))
                bot.send_message(ADMIN, f"User {userID} added to database.")
                bot.send_message(userID, 'You are succesfully added to the bot to submit jobs.')


def trimMe(myStr):
    return myStr[:10]+'...' if len(myStr)>13 else myStr


with open('.key') as f:
    # file written as <bot_API_key> <my_key>
    myKey,ADMIN = f.read().strip().split()
    bot= telebot.TeleBot(myKey, parse_mode='HTML')


logger = makeLogger('stat.log')
db = DataBase('sqlite3.db')


# Core Telegram bot message handlers

@bot.message_handler(commands='start')
def send_welcome(message):
    # Send a welcome message and request registration to admin
    user = message.from_user
    bot.send_message(user.id, f"Hi there {user.first_name} {user.last_name}. "
        "Welcome to this automated bot. This bot keeps track of your running jobs "
        "and send you notification when your job is complete or failed. "
        f"Your id is <b>{user.id}</b>. Use this when submitting jobs.")
    if not db.checkIfRegisteredUser(user):
        bot.send_message(user.id,"Note: You are not authorised to submit job with the bot "
        "Please wait for the admin to accept your request.")


@bot.message_handler(commands='listjobs')
def send_listRunningJobs(message):
    # List Running jobs for the current user
    user = message.from_user
    logger.info(f'List of running jobs requested for user={user.id}')
    if db.checkIfRegisteredUser(user):
        jobs,_ = db.listRunningJobs(user.id)
        bot.send_message(user.id,jobs)
    else:
        bot.send_message(user.id,'You are not authorised to use this option.')


@bot.message_handler(commands='listalljobs')
def send_listAllJobs(message):
    # List all jobs for the current user
    user = message.from_user
    logger.info(f'List of all jobs requested for user={user.id}')
    if db.checkIfRegisteredUser(user):
        jobs,_ = db.listAllJobs(user.id)
        bot.send_message(user.id,jobs)
    else:
        bot.send_message(user.id,'You are not authorised to use this option.')


@bot.message_handler(commands='myinfo')
def send_userinfo(message):
    # Send User Id of the user
    user = message.from_user
    logger.info(f'Information requested for {user.first_name} {user.last_name} ({user.id})')
    bot.send_message(user.id, f"Hi there {user.first_name} {user.last_name}. "
        f"Your id is <b>{user.id}</b>. Use this when submitting jobs")


@bot.message_handler(commands='remove')
def start(message):
    # Remove jobs for the users from database
    user = message.from_user
    logger.info(f'Requested to remove jobs for user={user.id}')
    if db.checkIfRegisteredUser(user):
        txt, count = db.listAllJobs(user.id)
        sent = bot.send_message(user.id, 'Provide serial number of jobs to remove.\n'+txt)
        if count : bot.register_next_step_handler(sent, removewithIDs)
    else:
        bot.send_message(user.id,'You are not authorised to use this option.')


def removewithIDs(message):
    # Remove jobs handlers
    toRemoveIds = [int(i) for i in re.split('[, ]+',message.text)]
    db.removeJob(message.from_user.id,toRemoveIds)
    bot.send_message(message.from_user.id, f'These jobs are removed {",".join([str(i) for i in toRemoveIds])}')


@bot.message_handler(func=lambda message: True)
def echo_all(message):
    # User registration only for the Admin
    if message.from_user.id==int(ADMIN) and message.text.lower().startswith('register'):
        newUserID = message.text.split()[1]
        logger.info(f'New user registration requested for {newUserID}')
        db.registerUser(newUserID)


# start the bot and http server in different thread
threading.Thread(target=bot.infinity_polling,daemon=True).start()
runServer()