import simplejson
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot, threading, os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlite3 import connect as sqlConnect
from operator import itemgetter
import logging


class MyServer(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_GET(self, userID):
        with sqlConnect('./sqlite3.db') as con:
            cur = con.cursor()
            cur.execute(f'Select * where Id=?',(userID))
            data = cur.fetchall()
        self._set_headers()

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        # Doesn't do anything with posted data

        try:
            content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
            post_data = self.rfile.read(content_length) # <--- Gets the data itself
            data = simplejson.loads(post_data)
            userId, host, job, status = itemgetter('id', 'host', 'job', 'status')(data)
            userId = int(userId)

            if(status=='start'):
                db.addJob(userId, host, job)
                bot.send_message(userId, f'A new job <i>{job}</i> is submitted on <b>{host}</b>')
            else:
                db.removeJob(userId, host, job)
                txt = 'is now complete.' if status=='complete' else 'has failed.'
                bot.send_message(userId, f'Your job <i>{job}</i> on <b>{host}</b>  {txt}')
            self.send_response(200)
        except Exception as e:
            self.send_response(500)
            print('failed', e)

        self._set_headers()
        self.end_headers()

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


def makeLogger(logFile, stdout=False):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = MyFormatter()
    fh = logging.FileHandler(logFile)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger



sqlScript = '''
CREATE TABLE JOBINFO(
Id INTEGER KEY,
host TEXT NOT NULL,
job TEXT NOT NULL);'''


class DataBase:
    def __init__(self, dbFile):
        self.dbFile = dbFile
        if not os.path.exists(dbFile): # create the database
            with sqlConnect(self.dbFile) as con:
                cur = con.cursor()
                cur.executescript(sqlScript)
        

    def listJobs(self,userID):
        # print(userID, type(userID))
        with sqlConnect(self.dbFile) as con:
            cur = con.cursor()
            cur.execute(f'Select host,job from JOBINFO where Id=?',(userID,))
            data = cur.fetchall()        
        if len(data):
            data = [[f'{l}. {i}',j] for l,(i,j) in enumerate(data, start=1)]
            lens = [max([len(i)+1 for i in a]) for a in list(zip(*data))]
            txt = [[i.ljust(lens[k]) for k,i in enumerate(j)] for j in data]
            header = '  '.join(['Host'.center(lens[0]), "Job".center(lens[1])])
            txt = "The follwing jobs are running:\n\n <pre>" +header+'\n'+'-'*30+'\n'+'\n'.join(['  '.join(i) for i in txt])+'</pre>'
        else:
            txt = "No running jobs found"
        return txt

    def addJob(self,userId, host, job):
        with sqlConnect(self.dbFile) as con:
            cur = con.cursor()
            cur.execute(f'Insert into JOBINFO values (?,?,?)',(userId,host,job))
            
    def removeJob(self,userId, host, job):
        with sqlConnect(self.dbFile) as con:
            cur = con.cursor()
            cur.execute(f"Delete from JOBINFO where id=? and host=? and job=?",(userId,host,job))
            



logger = makeLogger('stat.log')
db = DataBase('sqlite3.db')


with open('.key') as f:
    myKey = f.read().strip()
    bot= telebot.TeleBot(myKey, parse_mode='HTML')



@bot.message_handler(func=lambda message: True) # allow all filter inside
def echo_all(message):
    user = message.from_user
    command = message.text.lower()
    logger.info('ghegirhei')
    print(f'Incoming message from {user.first_name} {user.last_name} ({user.id} )')
    if(command=='hi'):
        bot.send_message(user.id, f"Hi there {user.first_name} {user.last_name}. Welcome to this automated bot. Your id is <b>{user.id}</b>. Use this when submitting jobs")
    elif(command=='listjobs'):
        userID = user.id
        jobs = db.listJobs(userID)
        bot.send_message(user.id, jobs)
    else:
        pass


threading.Thread(target=bot.polling,daemon=True).start()
runServer(addr="0.0.0.0",port=8080)




#TODO:1
# 1. bash submit job without the inverted comma
# 2. notify user during submiting the job if the messege is sent successfully ---
# 3. Place number to list of jobs ----