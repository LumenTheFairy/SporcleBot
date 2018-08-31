# Written by TheOnlyOne ( https://github.com/LumenTheFairy/ )

# used for states of a quiz and types of elements
from enum import Enum, auto

# set up logging
import logging
FORMAT = "[%(levelname)s] %(asctime)-15s: %(message)s"
logging.basicConfig(format=FORMAT)
log = logging.getLogger('sporcle')
log.setLevel(logging.DEBUG)
# log.setLevel(logging.WARNING)
log.debug("Sporcle logger has been set up.")

# get configurations for firefox
config_file = "sporcle_config.ini"
import configparser
config = configparser.ConfigParser()
config.read(config_file)
log.debug("Firefox config has been parsed.")

# # setup waiting
# import time
# waittime = float(config['Firefox']['waittime'])
# if not waittime:
#     waittime = 1.0
# def wait():
#     time.sleep(waittime)
# log.debug("Wait time set to " + str(waittime) + ".")



# import various things from selenium that we'll need
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import *

# enum containing constant names for relevant elements in the DOM
class SporcleElems(Enum):
    BTN_PLAY = auto()
    BTN_PREV = auto()
    BTN_NEXT = auto()
    BTN_PAUSE = auto()
    BTN_RESUME = auto()
    BTN_GIVE_UP = auto()
    BTN_EMBEDED = auto()

    INP_GUESS = auto()

    TXT_SCORE = auto()
    TXT_TIME = auto()
    TXT_FORCED_ORDER = auto()
    TXT_WRONG_ANSWER = auto()
    TXT_GAME_OVER = auto()

    SLT_SLOT = auto()
    SLT_NAME = auto()
    SLT_EXTRA = auto()

class SporcleDriver(webdriver.Firefox):
    """Subclass of the webdriver's Firefox driver that adds Sporcle quiz page-specific
    element lookup and existence checking."""

    # this lookup table provides the base way to get particular elements on a Sporcle quiz page
    # since we do not control Sporcle, the required lookup method for an element may change without notice
    # if Sporcle decides to change names of various things on their pages.
    # We try to contain what should need to change in such cases here (barring major Sporcle redesigns).
    #
    # Some elements (such as the list of correct answers) may be parametrized, so this table actually gives back functions,
    # which return a pair containing the correct element finding method and the string to pass to that method
    elem_lookup = {
        SporcleElems.BTN_PLAY : (lambda p : ("find_elements_by_id", "button-play")),
        SporcleElems.BTN_PREV : (lambda p : ("find_elements_by_id", "previousButton")),
        SporcleElems.BTN_NEXT : (lambda p : ("find_elements_by_id", "nextButton")),
        SporcleElems.BTN_PAUSE : (lambda p : ("find_elements_by_id", "pauseBox")),
        SporcleElems.BTN_RESUME : (lambda p : ("find_elements_by_id", "resumeBtn")),
        SporcleElems.BTN_GIVE_UP : (lambda p : ("find_elements_by_id", "giveUp")),
        SporcleElems.BTN_EMBEDED : (lambda p : ("find_elements_by_id", "embedMedia")),

        SporcleElems.INP_GUESS : (lambda p : ("find_elements_by_id", "gameinput")),

        SporcleElems.TXT_SCORE : (lambda p : ("find_elements_by_class_name", "currentScore")),
        SporcleElems.TXT_TIME : (lambda p : ("find_elements_by_id", "time")),
        SporcleElems.TXT_FORCED_ORDER : (lambda p : ("find_elements_by_id", "forcedOrder")),
        SporcleElems.TXT_WRONG_ANSWER : (lambda p : ("find_elements_by_id", "wrongAnswer")),
        SporcleElems.TXT_GAME_OVER : (lambda p : ("find_elements_by_id", "postGameBox")),

        SporcleElems.SLT_SLOT : (lambda p : ("find_elements_by_id", "slot" + str(p))),
        SporcleElems.SLT_NAME : (lambda p : ("find_elements_by_id", "name" + str(p))),
        SporcleElems.SLT_EXTRA : (lambda p : ("find_elements_by_id", "extra" + str(p))),
    }

    # returns true if the element is on the page, false otherwise
    def has_elem(self, elem_name, params=None):
        (finder, tag) = self.elem_lookup[elem_name](params)
        return len(getattr(self, finder)(tag)) > 0

    # returns an element of the given type
    # does not first check if the element exists, so it may raise an exception
    def get_elem(self, elem_name, params=None):
        (finder, tag) = self.elem_lookup[elem_name](params)
        return getattr(self, finder)(tag)[0]

    # submits a guess exactly, instead of one character at a time, as send_keys would
    # it is also synchronous, so there is no need to wait after the call
    # unfortunately requires executing js, so this might be dangerous
    # returns True if there were no problems, False otherwise
    def submit_guess(self, guess):
        try:
            guess = "".join(c for c in guess if c.isalnum() or c == ' ')
            if self.has_elem(SporcleElems.INP_GUESS):
                guess_box = self.get_elem(SporcleElems.INP_GUESS)
                self.execute_script('arguments[0].value = "' + guess + '"; checkGameInput(arguments[0]);', guess_box)
                return True
            return False
        except:
            log.exception("Exception raised while submitting guess via javascript.")
            return False

    def __init__(self, startpage="https://www.sporcle.com/"):
        # load our Firefox Profile from the config
        try:
            profile = config['Firefox']['profile']
            if profile:
                ffprofile = webdriver.FirefoxProfile(config['Firefox']['profile'])
                log.debug("Profile loaded.")
            else:
                ffprofile = webdriver.FirefoxProfile()
                log.debug("Using default profile.")
        except:
            log.exception("Error loading firefox profile. Using default profile instead.")
            ffprofile = webdriver.FirefoxProfile()

        # open the browser
        try:
            super().__init__(firefox_profile=ffprofile) 
            # firefox = webdriver.Firefox(firefox_profile=ffprofile)
        except:
            log.exception("Failed to open Firefox browser.")
            raise

        # open to the given starpage
        self.get(startpage)
        log.debug("Webpage " + startpage + "loaded.")
        


class SporcleQuiz:
    """Given a browser driver that is on a webpage containing an unstarted Sporcle quiz,
    this class provides functionality for remotely controlling that quiz."""

    # possible states of a quiz
    class QuizState(Enum):
        UNSTARTED = auto()
        PLAYING = auto()
        PAUSED = auto()
        FINISHED = auto()

    #TODO: display string

    # create an unstarted quiz
    def __init__(self, sporcle):
        self.sporcle = sporcle
        self.state = self.QuizState.UNSTARTED

        # get score values
        try:
            score_text = self.sporcle.get_elem(SporcleElems.TXT_SCORE).text
            [self.current_score, self.max_score] = map(int, score_text.split("/"))
        except:
            self.current_score = 0
            self.max_score = 0

        # check for forced order
        self.forced_order = False
        if self.sporcle.has_elem(SporcleElems.TXT_FORCED_ORDER):
            log.debug("Forced order!")
            self.forced_order = True
            # fill slots with their numbers so they can be referenced
            for slot_num in range(0, self.max_score):
                if self.sporcle.has_elem(SporcleElems.SLT_SLOT, slot_num):
                    slot_elem = self.sporcle.get_elem(SporcleElems.SLT_SLOT, slot_num)
                    script = 'arguments[0].innerHTML = "[' + str(slot_num+1) + ']";'
                    self.sporcle.execute_script(script, slot_elem)

        # self.full_time =
        # self.total_guesses = 0
        # self.correct_answers = Set.empty()
        # self.wrong_answers = False

    # start the quiz
    # returns True on success, False if there was a problem starting the quiz
    def start_quiz(self):

        # actually click the play button
        if self.sporcle.has_elem(SporcleElems.BTN_PLAY):
            # TODO: start embeded media
            self.sporcle.get_elem(SporcleElems.BTN_PLAY).click()
            self.state = self.QuizState.PLAYING
        else:
            return False
        return True

    # end the quiz, setting relevant stats
    def end_quiz(self):
        self.state = self.QuizState.FINISHED
        # TODO: more stuff

    # pause an active quiz
    # returns True on success, False if there was a problem pausing the quiz
    def pause_quiz(self):

        # click on pause button
        if self.sporcle.has_elem(SporcleElems.BTN_PAUSE):
            self.sporcle.get_elem(SporcleElems.BTN_PAUSE).click()
            self.state = self.QuizState.PLAYING
        else:
            return False
        return True

    # resume a paused quiz
    # returns True on success, False if there was a problem resuming the quiz
    def resume_quiz(self):

        # click on resume button
        if self.sporcle.has_elem(SporcleElems.BTN_RESUME):
            self.sporcle.get_elem(SporcleElems.BTN_RESUME).click()
            self.state = self.QuizState.PLAYING
        else:
            return False
        return True

    # returns True if the game has ended (evidenced by the existence of the post game info box), False otherwise
    def check_game_over(self):
        if self.sporcle.has_elem(SporcleElems.TXT_GAME_OVER):
            game_over_box = self.sporcle.get_elem(SporcleElems.TXT_GAME_OVER)
            return game_over_box.get_attribute("style") == ""
        return False

    # guess an answer
    # returns a dictionary containing information about the response:
    # (correct: boolean saying if this was a correct answer,
    #  ended: boolean saying if the quiz is over as a result of, or during, this guess
    #  already_accepted: boolean saying if this is an answer that was already accepted before)
    def guess_answer(self, guess):
        result = {
            "correct" : False,
            "ended" : False,
            "already_accepted" : False,
        }
        # sanitize the guess by leaving only alphanumeric characters and spaces
        guess = "".join(c for c in guess if c.isalnum() or c == ' ')

        # if this is a forced order quiz, the first word of the guess could be the slot for which the guess is intended
        if self.forced_order:
            # try to got the slot tag
            split_guess = guess.split(' ', 1)
            if len(split_guess) == 2:
                if split_guess[0].isdigit():
                    slot = int(split_guess[0]) - 1
                    if 0 <= slot < self.max_score:
                        guess = split_guess[1]
                        # jump to that slot
                        if self.sporcle.has_elem(SporcleElems.SLT_SLOT, slot):
                            slot_elem = self.sporcle.get_elem(SporcleElems.SLT_SLOT, slot)
                            slot_elem.click()


        if self.state == self.QuizState.PLAYING and guess != "":

            # check if the game ended
            if self.check_game_over():
                self.end_quiz()
                result["ended"] = True
                return result
            # submit the guess
            if not self.sporcle.submit_guess(guess):
                # there was an error submitting the guess
                return result
            # check if the game ended
            if self.check_game_over():
                self.end_quiz()
                result["ended"] = True
                return result
            # check the result of making the guess
            input_field = self.sporcle.get_elem(SporcleElems.INP_GUESS)
            current_value = input_field.get_property("value")
            # guess was not accepted
            if current_value == guess:
                input_field.clear()
            # guess was accepted
            elif current_value == "":
                result["correct"] = True
            # otherwise something strange has happened; log an warning
            else:
                log.warning("Part of a submitted guess was accepted.")
                input_field.clear()
        return result


# Bellow is a way to test the classes in this file by themselves, without the irc bot

# # you can replace the quiz url here with one you'd rather play
# sporcle = SporcleDriver("https://www.sporcle.com/games/g/pokemon")

# # create the quiz object
# quiz = SporcleQuiz(sporcle)

# # wait for any input to start
# input("Enter anything to start! After starting, an empty guess will end the quiz.")
# quiz.start_quiz()

# guess = "A guess"
# while guess:
#     guess = input("Guess: ")
#     result = quiz.guess_answer(guess)
#     if quiz.state == SporcleQuiz.QuizState.FINISHED:
#         log.debug("The quiz is over.")
#     log.debug(str(result))

# sporcle.close()