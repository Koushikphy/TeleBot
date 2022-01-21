This project is now archived, please check the alternative https://github.com/Koushikphy/TeleJobReminder.

## A Telegram bot that keeps track of your computer jobs
Telegram bots are an extermely useful way to send automated notification/message directly to phone. Its completely free, easy to set up and you can send any kind of messagages including document, pictures, videos etc. as long as its connected to the internet. Here, I have made a bot to keep track of my long running computer jobs, so that it can send me notification when the job finishes/fails.


### Setting up:
1. Create your Telegram bot and get the API key.
1. Create a `.key` file in the repo home and put your bot API key and your Telegram ID. 
1. Start the bot server `server.py`.
1. Modify the `telebot` with the server address where the bot server is running. Now you can use the `telebot` script to communicate with the bot from anywhere in the network where the bot server is running.
1. Open the bot in Telegram and start. A notification will be sent to the Admin to register the user. Note your user ID, it will be required to submit the jobs.
1. Submit your job with the shell script as
    ```
    telebot -u USER_ID -n JOB_Name -j JOB_Command
    ```

### NOTE: 
1. Python 3.6+ is required to use this.
1. Make sure you have `curl` and `pyTelegramBotAPI` installed.
2. The server-client architecture is not required to run the bot, but its setup here in that way so that the bot can run in a single place and the client can provide information to bot from anywhere on the network.


### Useful Links:
[Telegram Bots: An introduction for developers.](https://core.telegram.org/bots)
