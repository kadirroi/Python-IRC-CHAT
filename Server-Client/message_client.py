# -*- coding: cp1254 -*-
import sys
import socket
import threading
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import Queue
import time
class ReadThread (threading.Thread):
    def __init__(self, name, csoc, threadQueue, app):
        threading.Thread.__init__(self)
        self.name = name
        self.csoc = csoc
        self.nickname = ""
        self.threadQueue = threadQueue
        self.app = app

    def incoming_parser(self, data):
        print(data)
        if len(data) == 0:
            return
        if len(data) > 3 and not data[3] == " ":
            response = "ERR"
            self.csoc.send(response)
            return
        rest = data[4:]
        
        if data[0:3] == "BYE":
            self.app.cprint("-Server- BYE "+rest)
            return "QUIT"
            
        if data[0:3] == "ERL":
             self.app.cprint("-Server- Nick  not registered")
           

        if data[0:3] == "HEL":
            self.app.cprint("-Server-Registered as <"+rest+">")
            self.nickname=rest
       
        if data[0:3] == "REJ":
            self.app.cprint("-Server-Reject <"+rest+">")
           
        if data[0:3] == "MOK":
            self.app.cprint("-Server- Your message has been sent")
            
            
        if data[0:3] == "MNO":
            self.app.cprint("-Server- Failed to send your message")
           

        if data[0:3] == "MSG":
            print(data)
            if data[4:data.index(":")]==self.nickname:
                self.app.cprint("Message "+data[data.index(":")+1:data.index(";")]+": "+data[data.index(";")+1:])
                
            
        if data[0:3] == "TOC":
            self.app.cprint("-Server- Server is running")
            
        if data[0:3] == "SAY":
            user=data[4:data.index(":")]
            message=data[data.index(":")+1:]
            self.app.cprint("<"+user+">:"+message)
            
            print("SAY")

        if data[0:3] == "SYS":
            if not rest == self.nickname:
                self.app.cprint("-Server-"+rest+" "+"has joined")
            print("SYS")
        if data[0:3] == "LSA":
            splitted = rest.split(":")
            msg = "-Server- Registered nicks: "
            for i in splitted:
                msg += i + ","
            msg = msg[:-1]

            self.app.cprint(msg)

    def run(self):
        while True:
            
            data = self.csoc.recv(4096)
            
            dat=self.incoming_parser(data)
            if dat=="QUIT":
                break
class WriteThread (threading.Thread):
    def __init__(self, name, csoc, threadQueue):
        threading.Thread.__init__(self)
        self.name = name
        self.csoc = csoc
        self.threadQueue = threadQueue
    def run(self):
         while True:
             if self.threadQueue.qsize() > 0:
                 queue_message = self.threadQueue.get()
                 try:
                     #self.csoc.send(queue_message)
                     print("Queuue :"+ queue_message)
                     self.csoc.send(str(queue_message))
                     if queue_message=="QUIT":
                         break
                 except socket.error:
                     self.csoc.close()
                     break
class ClientDialog(QDialog):
    def __init__(self, threadQueue):
        self.threadQueue = threadQueue
# create a Qt application --- every PyQt app needs one
        self.qt_app = QApplication(sys.argv)
# Call the parent constructor on the current object
        QDialog.__init__(self, None)
# Set up the window
        self.setWindowTitle('IRC Client')
        self.setMinimumSize(500, 200)
# Add a vertical layout
        self.vbox = QVBoxLayout()
# The sender textbox
        self.sender = QLineEdit("", self)
# The channel region
        self.channel = QTextBrowser()
# The send button
        self.send_button = QPushButton('&Send')
# Connect the Go button to its callback
        self.send_button.clicked.connect(self.outgoing_parser)
# Add the controls to the vertical layout
        self.vbox.addWidget(self.channel)
        self.vbox.addWidget(self.sender)
        self.vbox.addWidget(self.send_button)
# A very stretchy spacer to force the button to the bottom
# self.vbox.addStretch(100)
# Use the vertical layout for the current window
        self.setLayout(self.vbox)
    def cprint(self, data):
        self.channel.append(data)
    def outgoing_parser(self):
            data = self.sender.text()
            self.cprint("-Local-:"+data)
            
            
            if len(data) == 0:
                return
            if data[0] == "/":
                if len(data)<=5:
                    command=data[1:]
                else:
                    command=data[1:data.indexOf(" ")]
                if command=="nick":
                    data2=data[data.indexOf(" ")+1:]
                    self.threadQueue.put("USR "+data2)
                elif command == "list":
                    
                    self.threadQueue.put("LSQ")

                elif command == "quit":
                    self.threadQueue.put("QUIT")
                elif command == "tic":
                    self.threadQueue.put("TIC")

                elif command == "msg":
                    data2=data[data.indexOf(" ")+1:data.lastIndexOf(" ")]
                    message=data[data.lastIndexOf(" ")+1:]
                    self.threadQueue.put(str("MSG "+data2+":"+message))
                    print("MSG "+data2+":"+message)
                else:
                    self.cprint("Local: Command Errordassa.")
            else:
                self.threadQueue.put("SAY " + data)
            self.sender.clear()

    def run(self):
        self.show()
        self.qt_app.exec_()
        
# connect to the server
host=str(sys.argv[1])
port=int(sys.argv[2])
s = socket.socket()
#host = socket.gethostname()
#port = 68
#host="127.0.0.1"
#port=12345
s.connect((host,port))
sendQueue = Queue.Queue()
app = ClientDialog(sendQueue)

# start threads
rt = ReadThread("ReadThread", s, sendQueue, app)
rt.start()
wt = WriteThread("WriteThread", s, sendQueue)
wt.start()
app.run()
rt.join()
wt.join()
s.close()
