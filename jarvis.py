#!/usr/bin/env python
# -*- coding: utf-8 -*-

# jarvis.py
# [rohit nawani]

import websocket
import pickle
import json
import urllib
import requests
import sqlite3
import sklearn
# SKLEARN IMPORTS ONLY
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline


import botsettings # local .py,
TOKEN = botsettings.API_TOKEN
DEBUG = True

def debug_print(*args):
    if DEBUG:
        print(*args)


try:
    conn = sqlite3.connect("jarvis.db")
except:
    debug_print("Can't connect to sqlite3 database...")


def post_message(message_text, channel_id):
    requests.post("https://slack.com/api/chat.postMessage?token={}&channel={}&text={}&as_user=true".format(TOKEN,channel_id,message_text))


class Jarvis():

    def __init__(self): # initialize Jarvis
        self.JARVIS_MODE = None
        self.ACTION_NAME = None

        # SKLEARN STUFF HERE:
        ## build a pipleline class that behaves like a compound classifier ##
        self.BRAIN = Pipeline([('vect', CountVectorizer()),
                     ('tfidf', TfidfTransformer()),
                      ('clf', MultinomialNB()), ])


    def on_message(self, ws, message):
        m = json.loads(message)

        # only react to Slack "messages" not from bots (me):
        if m['type'] == 'message' and 'bot_id' not in m:

            ## QUIT TRAINING OR TESTING ##
            if m['text'] == 'done':
                msg = "OK. I'm finished "+self.JARVIS_MODE.lower()
                post_message(msg, m['channel'])
                self.JARVIS_MODE = None
                self.ACTION_NAME = None

            ######################################
            ############## TRAINING ##############
            ######################################

            ## ACTUAL TRAINING
            if(self.JARVIS_MODE == 'TRAINING' and self.ACTION_NAME != None):
                msg = "OK. I've got it! What else?"
                post_message(msg, m['channel'])
                ## Save training message to database
                c = conn.cursor()
                msg_txt = m["text"]
                action  = self.ACTION_NAME
                c.execute("INSERT INTO training_data (txt,action) VALUES (?, ?)", (msg_txt, action,))
                conn.commit()  # save (commit) the changes


            ## 1ST MESSAGE AFTER TRAINING INITIATION
            if(self.JARVIS_MODE == 'TRAINING' and self.ACTION_NAME == None):
                msg = "OK. Let's call this action `" + m['text'] + "`. Now give me some training text!!"
                post_message(msg, m['channel'])
                self.ACTION_NAME = m['text']

            # INITIALISE TRAINING
            if m['text'] == 'training time':
                msg = "OK. I'm ready for training. What name should this ACTION be?"
                post_message(msg, m['channel'])
                self.JARVIS_MODE = 'TRAINING'

            ######################################
            ############## TESTING ###############
            ######################################

            ## ACTUAL TESTING
            if(self.JARVIS_MODE == 'TESTING'):
                ## USE BRAIN CLASSIFIER TO PREDICT ACTION NAME
                predicted_action = self.BRAIN.predict([m['text']])[0]
                msg = "OK, I think the action you mean is `" + predicted_action + "`..."
                post_message(msg, m['channel'])
                msg = "Write me something else and I'll try to figure it out."
                post_message(msg, m['channel'])


            # Initialise Testing
            if m['text'] == 'testing time':
                msg = "I'm training my brain with the data you've already given me..."
                post_message(msg, m['channel'])
                msg = "OK, I'm ready for testing. Write me something and I'll try to figure it out."
                post_message(msg, m['channel'])
                self.JARVIS_MODE = 'TESTING'
                ## Pour data into two lists
                c = conn.cursor()
                action_name_list = [ row[2] for row in c.execute("SELECT * from training_data") ]
                data_list = [ row[1] for row in c.execute("SELECT * from training_data") ]
                ## Pour data into the BRAIN
                ## ONLY FIT DATA WHEN USER DEMANDS TESTING TIME!!
                self.BRAIN.fit(data_list, action_name_list)




def start_rtm():
    """Connect to Slack and initiate websocket handshake"""
    r = requests.get("https://slack.com/api/rtm.start?token={}".format(TOKEN), verify=False)
    r = r.json()
    r = r["url"]
    return r


def on_error(ws, error):
    print("SOME ERROR HAS HAPPENED", error)


def on_close(ws):
    conn.close()
    print("Web and Database connections closed")


def on_open(ws):
    print("Connection Started - Ready to have fun on Slack!")



r = start_rtm()
jarvis = Jarvis()
ws = websocket.WebSocketApp(r, on_message=jarvis.on_message, on_error=on_error, on_close=on_close)
ws.run_forever()
