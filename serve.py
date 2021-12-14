import simplejson
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot, threading, os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlite3 import connect as sqlConnect
from operator import itemgetter
import logging,traceback, re
import random, string,sys



class MyServer(BaseHTTPRequestHandler):
    def _set_headers(self, code=200):
        self.send_response(code)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", '10')
        self.end_headers()

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        logger.info('Incoming request')
        try:
            content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
            post_data = self.rfile.read(content_length) # <--- Gets the data itself
            data = simplejson.loads(post_data)
            userId, host, job, status, jobID = itemgetter('id', 'host', 'job', 'status', 'jobID')(data)
            userId = int(userId)

            if(status=='start'):
                jobID = db.addJob(userId, host, job)
                logger.info(f'New job added userID={userId}, host={host}, job={job}, jobID={jobID}')
                self._set_headers()
                self.wfile.write(str(jobID).encode())
                logger.info(f'New job added for user {userId} at {host} : {job}')
                bot.send_message(userId, f'A new job <i>{job}</i> is submitted on <b>{host}</b>')


            else:
                db.closeJob(jobID)  # jobID is primary key so no other info is required
                logger.info(f'Job removed userID={userId}, host={host}, job={job}, jobID={jobID}')

                txt = 'is now complete.' if status=='complete' else 'has failed.'
                logger.info(f'Job closed for user {userId} at {host} : {job}')

                bot.send_message(userId, f'Your job <i>{job}</i> on <b>{host}</b>  {txt}')
                self._set_headers()
                txt = 'is now complete.' if status=='complete' else 'has failed.'
        except Exception as e:
            logger.exception()
            print('failed', e)
            self._set_headers(500)


def runServer(addr='http://0.0.0.0',port=3128):
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
                cur.executescript( '''
                CREATE TABLE JOBINFO(
                jobID integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                userId INTEGER NOT NULL,
                host TEXT NOT NULL,
                job TEXT NOT NULL);''')


    def listJobs(self,userID):
        # print(userID, type(userID))
        with sqlConnect(self.dbFile) as con:
            cur = con.cursor()
            cur.execute('Select host,job from JOBINFO where userId=?',(userID,))
            data = cur.fetchall()
        if len(data):
            data = [[f'{l}. {i}',j] for l,(i,j) in enumerate(data, start=1)]
            lens = [max([len(i)+1 for i in a]) for a in list(zip(*data))]
            txt = [[i.ljust(lens[k]) for k,i in enumerate(j)] for j in data]
            header = '  '.join(['Host'.center(lens[0]), "Job".center(lens[1])])
            txt = "The follwing jobs are running:\n\n <pre>" +header+\
                '\n'+'-'*30+'\n'+'\n'.join(['  '.join(i) for i in txt])+'</pre>'
        else:
            txt = "No running jobs found"
        logger.info('List of jobs requested for user={userID}')
        return txt



    def addJob(self,userId, host, job):
        # return the add code
        with sqlConnect(self.dbFile) as con:
            cur = con.cursor()  
            cur.execute('Insert into JOBINFO (userId, host, job) values (?,?,?)',(userId,host,job))
            cur.execute("select seq from sqlite_sequence where name='JOBINFO'") # as it is primary key
            jobID, = cur.fetchall()[0]
            return jobID


    def closeJob(self,jobID):
        with sqlConnect(self.dbFile) as con:
            cur = con.cursor()
            cur.execute("Delete from JOBINFO where jobID=?",(jobID,))


    def removeJob(self, userId, index):
        with sqlConnect(self.dbFile) as con:
            cur = con.cursor()
            cur.execute('Select jobID from JOBINFO where userId=?',(userId,))
            jobIds = cur.fetchall()
            jobIdsToRemove= [jobIds[i-1] for i in index]
            cur.executemany("Delete from JOBINFO where jobID=? ",jobIdsToRemove)
            logger.info(f'Job(s) removed for user {userId} jobIDs : {" ".join([str(i) for (i,) in jobIdsToRemove])}')



logger = makeLogger('stat.log')
db = DataBase('sqlite3.db')


with open('.key') as f:
    # file written as <bot_API_key> <my_key>
    myKey,ADMIN = f.read().strip().split()
    bot= telebot.TeleBot(myKey, parse_mode='HTML')



@bot.message_handler(commands='start')
def send_welcome(message):
    user = message.from_user
    bot.send_message(user.id, f"Hi there {user.first_name} {user.last_name}.\
        Welcome to this automated bot. This bot keeps track of your running jobs\
        and send you notification when your job is complete or failed.\
        Your id is <b>{user.id}</b>. Use this when submitting jobs")



@bot.message_handler(commands='listjobs')
def send_listJobs(message):
    userID = message.from_user.id
    jobs = db.listJobs(userID)
    bot.send_message(userID,jobs)


@bot.message_handler(commands='myinfo')
def send_userinfo(message):
    user = message.from_user
    bot.send_message(user.id, f"Hi there {user.first_name} {user.last_name}.\
        Your id is <b>{user.id}</b>. Use this when submitting jobs")



@bot.message_handler(commands=['remove'])
def start(message):
    sent = bot.send_message(message.from_user.id, 'Provide serial number of jobs to remove.\n'+db.listJobs(message.from_user.id))
    bot.register_next_step_handler(sent, removewithIDs)

def removewithIDs(message):
    toRemoveIds = [int(i) for i in re.split('[, ]+',message.text)]
    db.removeJob(message.from_user.id,toRemoveIds)
    bot.send_message(message.from_user.id, f'These jobs are removed {" ".join([str(i) for i in toRemoveIds])}')



threading.Thread(target=bot.polling,daemon=True).start()
runServer(addr="0.0.0.0",port=8080)