# -*- coding: cp1254 -*-
import socket
import threading
import Queue
import time
import errno

class LoggerThread (threading.Thread):
    def __init__(self, name, logQueue, logFileName):
        threading.Thread.__init__(self)
        self.name = name
        self.lQueue = logQueue
        self.fileName=logFileName
    # dosyayi appendable olarak ac
        self.fid = open(self.fileName, "a")
    def log(self,message):
    # gelen mesaji zamanla beraber bastir
        t = time.ctime()
        self.fid.write(t+":"+" "+ message+"\n")
        self.fid.flush()
    def run(self):
        self.log("Starting " + self.name)
        while True:
            if self.lQueue.qsize() > 0:
                # lQueue'da yeni mesaj varsa
                # self.log() metodunu cagir
                to_be_logged =  self.lQueue.get()
                self.log(to_be_logged)
        self.log("Exiting" + self.name)
        self.fid.close()   

class WriteThread (threading.Thread):
    def __init__(self, name, cSocket, address,fihrist,threadQueue, logQueue ):
        threading.Thread.__init__(self)
        self.name = name
        self.cSocket = cSocket
        self.address = address
        self.lQueue = logQueue
        self.tQueue = threadQueue
      
        self.fihrist = fihrist
        self.nickname=""
        self.flag=False
    def run(self):
        self.lQueue.put("Starting " + self.name)
        
        while True:
            # burasi kuyrukta sirasi gelen mesajlari
            # gondermek icin kullanilacak
            
            if  self.tQueue.qsize()>0 or self.flag:
                if self.nickname=="":
                    self.nickname=self.tQueue.get()
                    self.flag=True
                if  self.fihrist[self.nickname].qsize()>0:
                    queue_message = self.fihrist[self.nickname].get()
                   
                     # gonderilen ozel mesajsa
                    if not queue_message[0]=="SAY" and len(queue_message)==3 and not queue_message=="QUI" :
                        message_to_send = "MSG "+str(queue_message[0])+":"+str(queue_message[1])+";"+str(queue_message[2]) 
                        self.cSocket.send(str(message_to_send)) 
               # genel mesajsa
                    elif queue_message[0]=="SAY":
                        message_to_send = "SAY "+str(queue_message[1])+":"+str(queue_message[2]) 
                        self.cSocket.send(str(message_to_send))   
                        print(message_to_send)
                    elif queue_message=="QUI":
                         # fihristten sil
                        del self.fihrist[self.nickname]
                        break
                    # hicbiri degilse sistem mesajidir    
                    else:
                        message_to_send = "SYS "+str(queue_message[1])
                        self.cSocket.send(str(message_to_send))
                   
        self.lQueue.put("Exiting " + self.name)



class ReadThread (threading.Thread):
    def __init__(self, name, cSocket, address,fihrist,threadQueue,logQueue):
        threading.Thread.__init__(self)
        self.name = name
        self.cSocket = cSocket
        self.address = address
        self.lQueue = logQueue
        self.fihrist = fihrist
        self.tQueue = threadQueue
       
        self.nickname=""
    def parser(self, data):
        #data = data.strip()
      
        # henuz login olmadiysa
        if not self.nickname and not data[0:3] == "USR":
            response="ERL"
            self.cSocket.send(response)
        else:
             # data sekli bozuksa
             if len(data)<3:
                response = "ERR"
                self.cSocket.send(response)
                return 0
             if data[0:3] == "USR":
                if len(data)>4 and data[3]==" " and not data[3:len(data)]==" ":
                    self.nickname = data[4:]
                    if not self.nickname in  self.fihrist:
                        # kullanici yoksa
                       
                        
                        response = "HEL " + self.nickname
                        self.cSocket.send(response)
                        self.fihrist[self.nickname]=Queue.Queue(10)
                      
                          # fihristi guncelle
                           #self.fihrist.update(...)
                        self.lQueue.put(self.nickname + " has joined.")
                        self.tQueue.put(self.nickname)
                        queue_message = ("SYS", self.nickname)
                        for items in self.fihrist.keys():
                            self.fihrist[items].put(queue_message)
                        return 0
                    else:
                        # kullanici reddedilecek
                        response = "REJ " + self.nickname
                        self.cSocket.send(response)
                        # baglantiyi kapat
                        # self.cSocket.close()
                        return 1
                else:
                     response = "ERR"
                     self.cSocket.send(response)
                    
             elif data[0:3] == "QUI":
                response = "BYE " + self.nickname
                self.cSocket.send(response)
                queue_message="QUI"
                self.fihrist[self.nickname].put(queue_message)
               
                # log gonder
                self.lQueue.put(self.nickname + " has left.")
                # baglantiyi sil
                self.cSocket.close()
                return queue_message
            

             elif data[0:3] == "LSQ":
                a=" "
                for i in self.fihrist.keys():
                    a=a+i+":"
                response="LSA"+a[:-1]
                self.cSocket.send(response)
             elif data[0:3] == "TIC":
                response="TOC"
                self.cSocket.send(response)
             elif data[0:3] == "SAY":
                if len(data)>4 and data[3]==" " and not data[4:]==" ":
                    message=data[4:]
                    queue_message = ("SAY", self.nickname, message)
                    for items in self.fihrist.keys():
                        self.fihrist[items].put(queue_message)
                    
                    response="SOK"
                    self.cSocket.send(response)
         
             elif data[0:3] == "MSG":
                
                c=":"
                if not data[4:]==" " and c in data[4:]:
                    to_nickname=data[4:data.index(":")]
                    message=data[data.index(":")+1:]
                    if not to_nickname in self.fihrist.keys():
                        response = "MNO"
                    else:
                        
                        queue_message = (to_nickname, self.nickname, message)
                        # gonderilecek threadQueueyu fihristten alip icine yaz
                        
                        self.fihrist[to_nickname].put(queue_message)
                        
                       
                        response = "MOK"
                    self.cSocket.send(response)

             
                 
             else:
                # bir seye uymadiysa protokol hatasi verilecek
                response = "ERR"
                self.cSocket.send(response)

        


    def run(self):
        self.lQueue.put("Starting " + self.name)
      
        while True:
              
              try:
                  incoming_data=self.cSocket.recv(1024)
              except socket.error ,e:
                  err=e.args[0]
                  if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                      time.sleep(1)
                      print 'No data available'
                      continue
                  else:
                      print("ERROR"+str(e))

              queue_message = self.parser(incoming_data)
             
              
              if(queue_message)=="QUI":
                  break
              

      
        
        self.lQueue.put("Exiting " + self.name)
        print(threading.activeCount())


userList={}


loggerQueue= Queue.Queue()



thread3=LoggerThread("LoggerThread",loggerQueue,"log.txt")
thread3.start()
s = socket.socket()
#host = socket.gethostname()
host="127.0.0.1"
print("host"+host)
port = 12345
s.bind((host, port))
s.listen(5)
threadCounter=0
threadCounter2=0
while True:
    loggerQueue.put("Waiting for connection")
    print "Waiting for connection"
    c, addr = s.accept()
    workQueue = Queue.Queue()
    loggerQueue.put("Got a connection from " + str(addr))
    print "Got a connection from ", addr
    threadCounter += 1
    thread = ReadThread("ReadThread"+str(threadCounter), c, addr,userList,workQueue,loggerQueue)
    threadCounter2 += 1
    thread2 = WriteThread("WriteThread"+str(threadCounter2), c, addr,userList,workQueue,loggerQueue)
   
    thread.start()
    thread2.start()
    
      
