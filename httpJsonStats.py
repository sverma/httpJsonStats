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

  def __init__ (self , configLoc , pidfile = "/tmp/httpJsonStats.pid" , stdin='/dev/null', stdout='/tmp/http.log', stderr='/tmp/http.err' ): 
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
    appGroupsToUrls = {} 
    lines = [] 
    for app,attrs in self._jsonStr.iteritems(): 
      hostL = attrs["host"] 
      hosts = hostL.split(',')
      for host in hosts:
        URL = "http://" + host
        if ( attrs["port"] ) : 
          URL = "http://" + host + ':' + attrs['port'] 
        for groupName,value in attrs["groups"].iteritems(): 
          type = groupName
          URI = URL + value["URN"] 
          temp = groupName
          appGroupsToUrls[temp] = URI
        for appGroup,URL in appGroupsToUrls.iteritems() : 
          metricJson = ""
          try :
            req = urllib2.Request( url = URL ) 
            metricJson = urllib2.urlopen(req) 
          except Exception , e:
            print "Couldn't open the URL :" , URL , " "  , e
          metricsDict = json.load(metricJson) 
          for metric,value in metricsDict.iteritems(): 
            now = int( time.time() )
            hostFormatted = re.sub(r'\.', '-', host) 
            lines.append("%s.%s.%s.%s %s %d"%(app,appGroup,hostFormatted,metric,value,now))
    message = '\n'.join(lines) + '\n'
    return message


  def sendMetrics (self , message):
    sock = socket()
    try:
      sock.connect( (self._CARBON_SERVER , self._CARBON_PORT) )
    except:
      print "Couldn't connect to %(server)s on port %(port)d, is carbon-agent.py running?" % { 'server':self._CARBON_SERVER, 'port':self._CARBON_PORT }
      sys.exit(1)
    sock.sendall(message)

  def run(self):  
    logging.basicConfig(format='%(asctime)s %(message)s' , level=logging.INFO)
    while True:
      message = self.getMetrics()
      logging.info ("sending message") 
      logging.info(message)

      self.sendMetrics(message)
      time.sleep(self._delay)

if __name__ == "__main__":
  statsOb = httpJsonStats("/home/saurabh.ve/httpJsonStats/config.json" )
  if len(sys.argv) == 2:
    if 'start' == sys.argv[1]:
      statsOb.start()
    elif 'stop' == sys.argv[1]:
      statsOb.stop()
    elif 'restart' == sys.argv[1]:
      statsOb.restart()
    elif 'debug' == sys.argv[1]:
      statsOb.run()
    else:
      print "Unknown command"
      sys.exit(2)
    sys.exit(0)
  else:
    print "usage: %s start|stop|restart|debug" % sys.argv[0]
    sys.exit(2)
