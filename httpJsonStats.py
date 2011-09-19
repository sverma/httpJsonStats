import urllib2
import simplejson as json
from socket import socket
import sys
import time 
import os
import re
import logging
from daemon import Daemon


class httpJsonStats(Daemon):

  def __init__ (self , configLoc , pidfile = "/tmp/httpJsonStats.pid" , stdin='/dev/null', stdout='/tmp/httpJson.log', stderr='/tmp/httpJson.log' ): 
    self.configLoc = configLoc
    self._jsonStr = "" 
    self._CARBON_SERVER = "server.domain.com"
    self._CARBON_PORT = 2003
    self._delay = 20
    self._stdin = stdin 
    self._stdout = stdout 
    self._stderr = stderr 
    self._pidfile = pidfile
    self._evaluateConfig()
    if self._jsonStr["global"]["GRAPHITE_SERVER"]:
      self._CARBON_SERVER = self._jsonStr["global"]["GRAPHITE_SERVER"]
    if self._jsonStr["global"]["GRAPHITE_PORT"]:
      self._CARBON_PORT = self._jsonStr["global"]["GRAPHITE_PORT"]
    if self._jsonStr["global"]["INTERVAL"]:
      self._delay =  self._jsonStr["global"]["INTERVAL"]
    if self._jsonStr["global"]["LOG_FILE"]:
      self._stdout =  self._jsonStr["global"]["LOG_FILE"]
    if self._jsonStr["global"]["ERR_LOG_FILE"]:
      self._stderr =  self._jsonStr["global"]["ERR_LOG_FILE"]
    if self._jsonStr["global"]["PID_FILE"]:
      self._pidfile =  self._jsonStr["global"]["PID_FILE"]
    del self._jsonStr["global"]
    Daemon.__init__(self , self._pidfile,self._stdin,self._stdout,self._stderr) 


  def _evaluateConfig (self) : 
    f = open ( self.configLoc , 'r' ) 
    self._jsonStr = json.load(f) 
    
  def getMetrics ( self) : 
    lines = [] 
    for app,attrs in self._jsonStr.iteritems(): 
      groupNamesToUrls = {} 
      hostL = attrs["host"] 
      hosts = hostL.split(',')
      for host in hosts:
        tempURL = ""
        for groupName,value in attrs["groups"].iteritems(): 
          if "port" in value.keys() : 
              tempURL = "http://" + host + ':' + value["port"]
          else : 
              tempURL = "http://" + host + ':' + attrs['port'] 
          URI = ""
          URL = tempURL 
          type = groupName
          URI = URL + value["URN"] 
          temp = groupName
          groupNamesToUrls[temp] = URI
          filter = "" 
          if 'filter' in value.keys():
            filter = value["filter"] 
            logging.info("Collecting data from  " + groupName + " applying filter " + "'" + filter + "'" )
          else : 
            logging.info("Collecting data from  " + groupName + " without applying any filter " ) 
            
          metricJson = ""
          try :
            req = urllib2.Request( url = URI ) 
            metricJson = urllib2.urlopen(req) 
          except Exception , e:
            logging.info ( "Couldn't open the URL : " +  URI ) 
          metricsDict = json.load(metricJson) 
          for metric,value in metricsDict.iteritems(): 
            now = int( time.time() )
            hostFormatted = re.sub(r'\.', '_', host) 
            if ( filter == "" ) : 
              lines.append("%s.%s.%s.%s %s %d"%(app,hostFormatted,groupName,metric,value,now))
            elif ( ( filter ) ) : 
              p = re.compile(filter, re.IGNORECASE)
              if ( p.match(metric) ) : 
                lines.append("%s.%s.%s.%s %s %d"%(app,hostFormatted,groupName,metric,value,now)) 
    return lines


  def sendMetrics (self , message):
    sock = socket()
    try:
      sock.connect( (self._CARBON_SERVER , self._CARBON_PORT) )
    except:
      print "Couldn't connect to %(server)s on port %(port)d, is carbon-agent.py running?" % { 'server':self._CARBON_SERVER, 'port':self._CARBON_PORT }
      return  
    sock.sendall(message)

  def run(self):  
    logging.basicConfig(format='%(asctime)s %(message)s' , level=logging.INFO)
    while True:
      message = self.getMetrics()
      logging.info ("sending message") 
      logging.info(message)

      message = '\n'.join(message) + '\n'
      self.sendMetrics(message)
      time.sleep(self._delay)

if __name__ == "__main__":
  statsOb = httpJsonStats("config.json" )
  if len(sys.argv) == 2:
    if 'start' == sys.argv[1]:
      statsOb.start()
      print "Daemon Started \n"  
    elif 'stop' == sys.argv[1]:
      statsOb.stop()
      print "Daemon Stopped \n"  
      
    elif 'restart' == sys.argv[1]:
      statsOb.restart()
      print "Daemon restarted \n"
    elif 'debug' == sys.argv[1]:
      statsOb.run()
    else:
      print "Unknown command"
      sys.exit(2)
    sys.exit(0)
  else:
    print "usage: %s start|stop|restart|debug" % sys.argv[0]
    sys.exit(2)
