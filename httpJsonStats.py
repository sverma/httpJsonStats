import urllib2
import simplejson as json
from socket import socket
import sys
import time 
import os
import re

def evaluateConfig ( configLoc = "./config.json" ) : 
  f = open ( configLoc , 'r' ) 
  jsonStr = json.load(f) 
  return jsonStr

def constructURLs ( jsonStr = None ) : 
  appGroupsToUrls = {} 
  lines = [] 
  for app,attrs in jsonStr.iteritems(): 
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



def main(): 
  CARBON_SERVER = 'carbonServer.directi.com'
  CARBON_PORT = 2003
  delay = 20 
  if len(sys.argv) > 1:
    delay = int( sys.argv[1] )
  sock = socket()
  try:
    sock.connect( (CARBON_SERVER,CARBON_PORT) )
  except:
    print "Couldn't connect to %(server)s on port %(port)d, is carbon-agent.py running?" % { 'server':CARBON_SERVER, 'port':CARBON_PORT }
    sys.exit(1)
  jsonStr = evaluateConfig() 
  while True:
    message = constructURLs(jsonStr) 
    print "sending message\n"
    print '-' * 80
    print message
    print
    sock.sendall(message)
    time.sleep(delay)

if __name__ == "__main__":
  main() 

