# original ircbot code by TestRunner ( https://github.com/TestRunnerSRL )
# sporcle bot integration by TheOnlyOne ( https://github.com/LumenTheFairy/ )
from sporcle_classes import SporcleQuiz, SporcleDriver


# set up logging
import logging
FORMAT = "[%(levelname)s] %(asctime)-15s: %(message)s"
logging.basicConfig(format=FORMAT)
log = logging.getLogger('ircbot')
log.setLevel(logging.DEBUG)
# log.setLevel(logging.WARNING)
log.debug("IRCBot logger has been set up.")

# get configurations for login information
config_file = "sporcle_config.ini"
import configparser
config = configparser.ConfigParser()
config.read(config_file)
HOST = config['Login']['host']
PORT = int(config['Login']['port'])
PASSWORD = config['Login']['token']
CHANNEL = config['Login']['channel']
NICK = config['Login']['user']
DELAY = float(config['Login']['start_delay'])
if not DELAY:
    DELAY = 10.0
log.debug("IRCBot config has been parsed.")


import socket
import threading
import re
import time

global TwitchIRC
global floodlock
global messagequeue
global curcolor
global readbuffer
global timeoutcount
global sporcle
global quiz

floodlock = 0
messagequeue = []
curcolor = "#000000"

# handle program interuption and properly close the socket
import signal
import sys
def signal_handler(signal, frame):
        log.debug("Quitting...")
        TwitchIRC.shutdown(socket.SHUT_RDWR)
        TwitchIRC.close()
        sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)


def lock_used():
    global floodlock
    return floodlock > 1


def take_lock():
    global floodlock
    floodlock += 1


def release_lock():
    global floodlock
    floodlock -= 1


# Method for sending a message to a channel
def send_message(msg, chan):
    global messagequeue

    if lock_used():
        messagequeue.append([msg, chan])
        return False

    take_lock()
    TwitchIRC.send(("PRIVMSG %s :%s\r\n" % (chan, msg)).encode('utf-8'))
    threading.Timer(1.0, release_lock).start()

    log.debug("> PRIVMSG %s :%s\r\n" % (chan, msg))
    return True

def check_message_queue():
    global messagequeue

    if len(messagequeue) == 0:
        return

    if lock_used():
        return

    [msg, chan] = messagequeue.pop(0)
    if not send_message(msg, chan):
        newmsg = messagequeue.pop()
        messagequeue.insert(0, newmsg)

    check_message_queue()


def change_color(color, chan=CHANNEL):
    global curcolor
    if color == curcolor:
        return False

    send_message("/color %s" % color, chan)
    curcolor = color
    return True


def send_color_message(msg, color, chan):
    if change_color(color, chan):
        time.sleep(2.0)
    send_message(msg, chan)


def command_start_quiz(message):
    global sporcle
    global quiz
    if not message['tags']['broadcaster']:
        return

    try:
        quiz = SporcleQuiz(sporcle)

        # TODO: give info on quiz and quiz type
        send_message('Get ready... To guess an answer, just type in chat, or whisper to me ("/w ' + NICK + ' guess").', CHANNEL)
        time.sleep(DELAY)

        quiz.start_quiz()
        send_message("Go!", CHANNEL)
    except:
        log.exception('Exception occurred while starting a quiz.')


commandlist = {
    '!start_quiz':command_start_quiz,
}



def process(line):
    global echo_enable

    # Checks whether the message is PING because its a method of Twitch to check if you're afk
    if line.startswith("PING "):
        TwitchIRC.send(bytes("PONG " + line[5:] + "\r\n", "utf-8"))
        #print("> PONG " + line[5:] + "\r\n")
        return

    # parse line
    match = re.match(r'@(.*) :([a-z0-9_]+)![a-z0-9_]+@[a-z0-9_]+\.tmi\.twitch\.tv ([A-Z]+) ([#a-z0-9_]+) :(.*)\r$',
        line)

    if not match:
        return

    message = {}
    [tags, message['user'], message['type'], message['channel'], message['message']] = match.groups()

    if message['type'] != 'PRIVMSG' and message['type'] != 'WHISPER':  # not a user message
        return

    # build tags dict
    temp = tags.split(';')
    message['tags'] = {}
    for tag in temp:
        [key, val] = tag.split('=', 1)
        message['tags'][key] = val
    message['tags']['broadcaster'] = message['tags']['badges'].find("broadcaster") > -1

    if not re.match(r'[a-zA-Z0-9_]+', message['tags']['display-name']):
        message['tags']['display-name'] += ' (%s)' % message['user']


    # handle slash me
    if re.match(r'\x01ACTION (.*)\x01', message['message']):
        message['message'] = re.sub(r'\x01ACTION (.*)\x01', r'\1', message['message'])

    # ignore self messages
    if message['user'] == NICK.lower() or message['user'] == 'nightbot':
        return

    message['split_message'] = message['message'].split(' ')
    command_func = commandlist.get(message['split_message'][0])
    if command_func:
        command_func(message)
        return

    # send the message as a guess
    global quiz
    if quiz and quiz.state == SporcleQuiz.QuizState.PLAYING:
        try:
            quiz.guess_answer(message['message'])
        except:
            log.exception('Exception occured while guessing an answer.')


def connect_twitch():
    global TwitchIRC
    global readbuffer
    global timeoutcount

    log.debug("Attempting connection to Twitch.")
    TwitchIRC = socket.socket()
    def sends(s): TwitchIRC.send(bytes(s, "utf-8"))
    TwitchIRC.connect((HOST, PORT))
    sends("PASS %s\r\n" % PASSWORD)
    sends("NICK %s\r\n" % NICK)
    sends("USER %s %s bla :%s\r\n" % (NICK, HOST, NICK))
    sends("CAP REQ :twitch.tv/membership\r\n")
    sends("CAP REQ :twitch.tv/commands\r\n")
    sends("CAP REQ :twitch.tv/tags\r\n")
    sends("JOIN %s\r\n" % CHANNEL)
    TwitchIRC.setblocking(0)

    readbuffer = ""
    timeoutcount = 0

# start the bot
connect_twitch()
send_message("Hello, I am Sporcle.", CHANNEL)
log.debug("If you did not see the above message, the connection has failed.")

# start the selenium stuff
sporcle = None
sporcle = SporcleDriver()
quiz = None

while True:
    time.sleep(1.0)


    check_message_queue()

    try:
        readbuffer = readbuffer + TwitchIRC.recv(4096).decode('utf-8')
        #if timeoutcount > 0:
        #    print('\n'),
        #print('[Timestamp: %s]' % datetime.datetime.now().time().isoformat())
        timeoutcount = 0

    except socket.error as e:
        timeoutcount += 1

        if timeoutcount >= 360:
            log.warn("Timeout error: " + timeoutcount + " seconds")
            log.debug("Closing socket.")
            TwitchIRC.shutdown(socket.SHUT_RDWR)
            TwitchIRC.close()
            connect_twitch()
            continue

        #print("\r[Timeout: %d seconds]" % timeoutcount),
        continue

    lines = readbuffer.split("\n")
    readbuffer = lines.pop()

    check_message_queue()

    for l in lines:
        #print("< %s" % l)
        process(l)
    #print('')