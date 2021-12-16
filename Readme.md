# A Telegram bot that keeps track of your jobs

### Setting up:
1. Create your Telegram bot using bot father and get the API key.
1. Create a `.key` file in the repo home and put your bot API key and your Telegram ID.
1. Start the bot server `server.py`.
1. Modify the `telebot` with the server address where the bot server is running.
1. Add userids in the database to allow jobs.
1. Submit your job with the shell script as
    ```
    telebot -u USER_ID -n JOB_Name -j JOB_Command
    ```
NOTE: Make sure you have `curl` and `pyTelegramBotAPI` installed.
