# What is SporcleBot?
SporcleBot is a [twitch.tv](http://twitch.tv) chat bot that allows a stream's chat to play a [Sporcle](https://www.sporcle.com/) quiz together. It does this by submitting every message in the chat as an answer to the currently running Sporcle quiz.

[Here is an example of SporcleBot in action.](https://www.twitch.tv/videos/302353313)

# How to use it
1. In order to be able to run SporcleBot, you will need to follow the setup instructions below.
2. Run the script:
    ```
    $ python sporclebot.py
    ```
This will do a few things. Firstly, your SporcleBot will connect to your twitch chat (and should confirm by sending the message "Hello, I am Sporcle."). Secondly, a new Firefox window will open up to [https://www.sporcle.com/](https://www.sporcle.com/). This can take a minute or two if you are loading an existing Firefox profile.
3. Navigate to a quiz in the Firefox window.
4. Send the message "!start_quiz" in twitch chat. The owner of the channel must do this. SporcleBot will then start the quiz and begin accepting answers after a short waiting period.
5. Play the quiz by typing answers in chat!
6. Repeat steps 3-5 forever (once you start playing Sporcle, you can never stop.....)

### Forced order quizes
In a basic Sporcle quiz, you do not need to tell the quiz which slot you intend an answer for; entering a correct answer fills it in in the correct spot automatically (this is especially true of "Name all of the ..." type quizzes where there really is no order anyway). However, some Sporcle quizes have a rule called "forced order" which causes the quiz to only take answers for the slot that is currently in focus (you can change focus to any slot at any time though).

SporcleBot handles forced order quizzes by filling the slots on the webpage with numbers, and then accepting guesses of the form `# guess` and moving focus to the specified slot before submitting the guess. So for example, if you were playing a quiz that asked you to [name the presidents in alphabetical order](https://www.sporcle.com/games/amehta/presidents_alphabetical), you would give answers like `1 Adams` or `26 Lincoln`. Some Sporcle quizzes shuffle the order of slots in forced order quizzes, so the order of the numbers may seem strange sometimes.

There are a handful of other quiz types (most involving clicking labels) that are not supported by SporcleBot.

# Setup
SporcleBot is a python program that uses Selenium to interact directly with a web browser in order to send quiz answers. It is also an irc bot that needs to be authorized to login and send messages to twitch chat. So in order to use SporcleBot, you will need to install the appropriate components, and supply a working configuration.

### Installation
You will need to install the following:

1. [Python 3](https://www.python.org/downloads/)
2. [Firefox](https://www.mozilla.org/download/)
3. Selenium for python:
    ```
    $ pip install selenium
    ```
4. Download Firefox's [geckodriver](https://github.com/mozilla/geckodriver/releases) and add it to your *PATH*

For more detailed information on Selenium/Gecko installation: [https://selenium-python.readthedocs.io/installation.html](https://selenium-python.readthedocs.io/installation.html)

### Configuration
Open up `sporcle_config.ini` in you favorite text editor, and set the following values:

* `user` This should be the twitch username of the bot that will be connecting to the chat (you will need to create an new account for this). It should look something like this: `user = sporclebot`
* `token` Go to [https://twitchapps.com/tmi/](https://twitchapps.com/tmi/) and login as the chat bot you set as the user. Authorize twitch to allow your bot to send messages. This will give you a token, which you should put here in the config. It will look something like this: `token = oauth:##############################`
* `channel` This should be the twitch username of the channel you want the bot to join and play in (probably your own channel). It should look like this: `channel = #theonly0` (note the `#` is required here).
* `start_delay` This lets you set the amount of time, in seconds, between sending "!start_quiz" and the quiz actually starting. This gives players time to read the quiz title and rules, especially if there is stream delay. It should look like this: `start_delay = 2.0`

Finally, there is an option `profile` that allows you to set a Firefox profile that the new window will use. Without specifying this, the window will use the default Firefox profile. You may want to set this if you have any plugins or visual options you want to use while using SporcleBot. Note that loading a profile can take a minute or two when you start up the bot. To find the profile Firefox normally loads, on Windows, it can typically be found at `C:\Users\MyName\AppData\Roaming\Mozilla\Firefox\Profiles\`. The setting may then look something like this: `profile = C:\Users\MyName\AppData\Roaming\Mozilla\Firefox\Profiles\########.default`.