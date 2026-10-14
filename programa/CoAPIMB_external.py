#Python 3 library for using IMB CoAP commands
#Your main program must import CoAPIMB eg "import CoAPIMB as imb"
#Main program also must use setupClient(IPaddress) in order for this library to work properly
################################################
#Most put commands will require a channel number and a payload as input. If no payload needed, use "NULL".

#Coapthon3 must be installed on the computer using pip install coapthon3
from coapthon.client.helperclient import HelperClient
import socket
import sys
import time
global logswitch
client=None 


def setupClient(IPaddress, log):
    global logswitch
    global host
    global port
    global client    
    host = IPaddress
    port = 5683    
    client = HelperClient(server=(host, port))
    logswitch = log
    if pingIMB():
        return True
    else:
        return False
    

###System###

def pingIMB():
    global logswitch
    if logswitch:
        print("Connecting to "+host+"..."+"\r\n")
    testimb = str(client.put("/ping", "NULL", timeout=3))
    #print(str(testimb))

    if "From" in testimb:
        if logswitch:
            print("Response from CoAP service OK...")
            print("")
        return True
    else:
        if logswitch:
            print("IMB not found. Check ethernet connection or hostname")
        return False
		
def NVread():
	client.put("/nv/read", "NULL")

def NVsave():
	client.put("/nv/save", "NULL")

def getSoftwareVersion():

    response = client.get("/ver/sw")
    return response.payload


def systemreset():    
    client.put("/board/reset","0")

def closeclient():
    client.close()

IMBHOST= '192.168.17.174'
IMBGRAPHPORT = 2004

def setupGraphConnection():
   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   if sys.platform == "win32":
       s.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 1000, 3000))
       s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
       print("Connecting socket")
       try:
           s.connect((IMBHOST, IMBGRAPHPORT))
       except ConnectionRefusedError:
           print("Connection refused")
           time.sleep(5)
           return 0
       else:
           print("Connected")           
           return s


###Channel state information###

def getTopState(channel):
     channel = str(channel)
     response = client.get("/state/top?uc="+channel)
     return response.payload

def getSubState(channel):
    try:
         channel = str(channel)
         response = client.get("/state/sub?uc="+channel)
         return response.payload
    except AttributeError:
         return False
     
def getBulkTank(channel):
    try:
        channel = str(channel)
        response = client.get("/bulktank/level?uc="+channel)
        return response.payload
    except AttributeError:
        return False

##Errors##

def getErrorCount():
     response = client.get("/error/allcount")
     return response.payload

def getAllErrorMsg():
     response = client.get("/error/latestallerror")
     return response.payload

def getAllErrorCode():
     response = client.get("/error/latestallcode")
     return response.payload


def getChannelErrorMsg(channel):
     channel = str(channel)
     response = client.get("/error/latestallerror")
     print("response.payload")
     print(response.payload)
     try: 
        response = response.payload.split("\t")
        if channel in response:
          location = response.index(channel)+1
          message = response[location]
          return message
     except:
      return("None")

def getWarnCount():
     response = client.get("/warn/allcount")
     return response.payload

def getAllWarnMsg():
     response = client.get("/warn/latestallwarn")
     return response.payload

def getAllWarnCode():
     response = client.get("/warn/latestallcode")
     return response.payload
        

def getChannelWarnMsg(channel):
     channel = str(channel)
     response = client.get("/warn/latestallwarn")
     try:
        response = response.payload.split("\t")
        if channel in response:
         location = response.index(channel)+1
         message = response[location]
         return message        
     except:
        return("None")

###Control commands###
    
def putAllIdle():
    client.put("/cmd/allidle", "NULL")

def putAllFlow():
    client.put("/cmd/allflow", "NULL")

def putAllReset():
    client.put("/cmd/allstop", "NULL")

def putAllPurge():
    client.put("/cmd/allpurge", "NULL")

def putVent(channel):
    channel = str(channel)
    client.put("/cmd/vent?uc="+channel, "NULL")

def putIdle(channel):
    channel = str(channel)
    client.put("/cmd/idle?uc="+channel, "NULL")

def putFlow(channel):
    channel = str(channel)
    client.put("/cmd/flow?uc="+channel, "NULL")

def applySettings(channel):
    channel = str(channel)
    client.put("/cmd/applysettings?uc="+channel, "NULL")

def putReset(channel):
    channel = str(channel)
    client.put("/cmd/stop?uc="+channel, "NULL")

def putPurge(channel):
    channel = str(channel)
    client.put("/cmd/purge?uc="+channel, "NULL")

###Vacuum control settings###

def getIdlePressure(channel):
     channel = str(channel)
     response = client.get("/s/va/IP?uc="+channel)
     return response.payload

def putIdlePressure(channel):
     channel = str(channel)
     response = client.put("/s/va/IP?uc="+channel)

###Channel Assignment###

def getNumHTBs(): #returns the number of assigned HTBs
    n=0
    for i in range (1,8):
        if getHTBAssign(i) > 0:
            n = n+1 
    return n

def getIndependentChannels():
    independents = [0,0,0,0,0,0,0,0]
    for i in range (1,8):
        topState = getTopState(i)
        if topState == "LowFlow" or topState == "ControlledFlow" or topState == "NoFlow" or topState == "HighPressureType2Flow":
           independents[i]=1
        else:
           independents[i]=0
    return independents
    

def getMasterChannels():
    masters = [0,0,0,0,0,0,0,0]
    for i in range (1,8):
        topState = getTopState(i)
        if topState == "LowFlowMaster" or topState == "ControlledFlowMaster" or topState == "NoFlowMaster" or topState == "HPType2FlowMaster":
           masters[i]=1
        else:
           masters[i]=0
    return masters
    

def getAssociatedSlaves(master):
    slaves = [0,0,0,0,0,0,0,0]
    for i in range (1,8):
        if int(getMasterAssign(i)) == master:
           slaves[i]=1
        else:
           slaves[i]=0
    return slaves

def removeAssociatedSlaves(master):
    removedslaves = [0,0,0,0,0,0,0,0]
    flowmode = getFlowMode(master)
    for i in range (1,8):
        if int(getMasterAssign(i)) == master:
           removedslaves[i]=1
           disMaster(i)
           putFlowMode(i, flowmode)           
           
        else:
           removedslaves[i]=0
    return removedslaves

def verifySlaveFlowmodes(master):
    incorrectslaves = [0,0,0,0,0,0,0,0]
    flowmode = getFlowMode(master)
    for i in range (1,8):
        if int(getMasterAssign(i)) == master and flowmode != getFlowMode(i):
           incorrectslaves[i] = 1
    return incorrectslaves


def reassignAssociatedSlaves(master, removedslaves):    
    flowmode = getFlowMode(master)
    for i in range (1,8):
        if removedslaves[i] == 1:
           putMasterAssign(i, master)           
           putFlowMode(i, flowmode)
    putFlowMode(master, flowmode)       

def getHTBAvail():
     
     response = client.get("/htbmgr/numhtbs")     
     return int(response.payload) #Returns -1 if no association

def putSlaveDisable(channel):
     
     response = client.put("/cmd/" + str(channel) + "/slave/disable", "NULL")

def putSlaveEnable(channel):
    response = client.put("/cmd/" + str(channel) + "/slave/enable", "NULL")

def putSingleSlaveEnable(channel):
    response = client.put("/cmd/" + str(channel) + "/slave/single", "NULL")

def putAllSlaveEnable(channel):
    response = client.put("/cmd/" + str(channel) + "/master/allslaveenable", "NULL")

def putAllSlaveDisable(channel):
    response = client.put("/cmd/" + str(channel) + "/master/allslavedisable", "NULL")


def getHeaterActuatorID(channel, act):
    channel = str(channel)
    act = str(act)
    response = client.get("/htbmgr/heater/"+channel+"/"+act+"/actid")    
    return response.payload


def getHTBAssign(channel):
     channel = str(channel)
     response = client.get("/assign/htb?uc="+channel)
     return int(response.payload) #Returns -1 if no association

def getVacAssign(channel):
     channel = str(channel)
     response = client.get("/assign/vacuum?uc="+channel)
     return int(response.payload) #Returns -1 if no association

def getButtonAssign(channel):
     channel = str(channel)
     response = client.get("/assign/button?uc="+channel)
     return int(response.payload) #Returns -1 if no association

def getInkAssign(channel):
     channel = str(channel)
     response = client.get("/assign/ink?uc="+channel)
     return int(response.payload) #Returns -1 if no association

def getFlowMode(channel):     
     response = client.get("/s/va/FLOWMODE?uc="+str(channel))
     return int(response.payload) 

def putFlowMode(channel, flowmode):     
     response = client.put("/s/va/FLOWMODE?uc="+str(channel), str(flowmode))     

def getMasterAssign(channel):     
     response = client.get("/assign/master?uc="+str(channel))
     return int(response.payload)

def disMaster(channel):
     channel = str(channel)
     response = client.put("/deassign/master?uc="+channel, "Null")       

def putMasterAssign(slave, master):     
     response = client.put("/assign/master?uc="+str(slave), str(master))     

def getSysMode():
     response = client.get("/system/cur_mode")
     return response.payload 

def getError():
     response = client.get("/error/latestallerror")
     return response.payload 

##Settings##


def getValidationID(channel):
     channel = str(channel)
     response = client.get("/fc/"+channel+"/validate/starttxact")
     return response.payload

def putValidationStoreIdlePressure(channel, pressure, tID):
     pressure = str(pressure)
     channel = str(channel)
     tID = str(tID)
     response = client.put("/fc/"+channel+"/vset/vac/IP/store?tid="+tID, pressure)

def validateIdlePressure(channel, tID):
     channel = str(channel)
     tID = str(tID)
     response = client.get("/fc/"+channel+"/vset/vac/IP/validate?tid="+tID)
     if response.payload == "0":
         return True
     else:
         return False

def putValidationStoreITPD(channel, itpd, tID):
     itpd = str(itpd)
     channel = str(channel)
     tID = str(tID)
     response = client.put("/fc/"+channel+"/vset/vac/ITPD/store?tid="+tID, itpd)

def putValidationStoreOTPD(channel, otpd, tID):
     otpd = str(otpd)
     channel = str(channel)
     tID = str(tID)
     response = client.put("/fc/"+channel+"/vset/vac/OTPD/store?tid="+tID, otpd)

def validateITPD(channel, tID):
     channel = str(channel)
     tID = str(tID)
     response = client.get("/fc/"+channel+"/vset/vac/ITPD/validate?tid="+tID)
     if response.payload == "0":
         return True
     else:
         return False

def validateOTPD(channel, tID):
     channel = str(channel)
     tID = str(tID)
     response = client.get("/fc/"+channel+"/vset/vac/OTPD/validate?tid="+tID)
     if response.payload == "0":
         return True
     else:
         return False

def getIdlePressure(channel):
     channel = str(channel)
     response = client.get("/fc/"+channel+"/cset/vac/IP/store")
     return response.payload

def putEndValidation(channel, tID):
     channel = str(channel)
     tID = str(tID)
     response = client.put("/fc/"+channel+"/validate/endtxact?tid="+tID, "NULL")
     if response.payload == "0":
         return True
     else:
         return False

def putIdlePressure(channel, pressure):
     pressure = str(pressure)
     channel = str(channel)
     client.put("/fc/"+channel+"/cset/vac/IP/store", pressure)

def putITPD(channel, itpd):
     itpd = str(itpd)
     channel = str(channel)
     client.put("/fc/"+channel+"/cset/vac/ITPD/store", itpd)

def putOTPD(channel, otpd):
     otpd = str(otpd)
     channel = str(channel)
     client.put("/fc/"+channel+"/cset/vac/OTPD/store", otpd)

def getITPD(channel):
     channel = str(channel)
     response = client.get("/fc/"+channel+"/cset/vac/ITPD/store")
     return response.payload

def setChannelPressures(channel, IP, ITPD, OTPD, applysettings):
     channel = str(channel)
     #Get Validation ID
     tID = getValidationID(channel)
     #Idle pressure to validation store
     putValidationStoreIdlePressure(channel, str(IP), tID)
     #ITPD pressure to validation store
     putValidationStoreITPD(channel, str(ITPD), tID)
     #OTPD pressure to validation store
     putValidationStoreOTPD(channel, str(OTPD), tID)
     #Validate idle pressure
     if validateIdlePressure(channel, tID) == False:
         print("IP FAIL on channel " + channel)     
         return False

     if validateITPD(channel, tID) == False:
         print("ITPD FAIL on channel " + channel)     
         return False

     if validateOTPD(channel, tID) == False:
         print("OTPD FAIL on channel " + channel)     
         return False
     
     #End validation transaction
     endtx = putEndValidation(channel, tID)

     #If the validation was OK then send the pressure setting to IMB
     if endtx == True: 
         putIdlePressure(channel, str(IP))
         putITPD(channel, str(ITPD))
         putOTPD(channel, str(OTPD))
         if applysettings:
                 applySettings(channel)
         if True:
            print("Pressures set on channel " + channel)
            
         return True
     else:
         if logswitch:
             print("Transaction error")
         return False


def setIdlePressure(channel, pressure):
     pressure = str(pressure)
     channel = str(channel)
     #Get Validation ID
     tID = getValidationID(channel)
     #Store Idle pressure 
     putValidationStoreIdlePressure(channel, pressure, tID)
     #Validate idle pressure
     validate = validateIdlePressure(channel, tID)
     #End validation transaction
     end = putEndValidation(channel, tID)

     #If the validation was OK then send the pressure setting to IMB
     if end == True and validate == True:
         putIdlePressure(channel, pressure)
         if logswitch:
            print("Idle pressure set to "+pressure)
         return True
     else:
         if logswitch:
             print("Idle pressure setting error")
         return False

def setITPD(channel, itpd):
     itpd = str(itpd)
     channel = str(channel)
     #Get Validation ID
     tID = getValidationID(channel)
     #Store ITPD
     putValidationStoreITPD(channel, itpd, tID)
     #Validate ITPD
     validate = validateITPD(channel, tID)
     #End validation transaction
     end = putEndValidation(channel, tID)

     #If the validation was OK then send the pressure setting to IMB
     if end == True and validate == True:
         putITPD(channel, itpd)
         print("ITPD set to "+itpd)
         return True
     else:
         print("ITPD setting error")
         return False

def setOTPD(channel, otpd):
     otpd = str(otpd)
     channel = str(channel)
     #Get Validation ID
     tID = getValidationID(channel)
     #Store ITPD
     putValidationStoreOTPD(channel, otpd, tID)
     #Validate ITPD
     validate = validateOTPD(channel, tID)
     #End validation transaction
     end = putEndValidation(channel, tID)

     #If the validation was OK then send the pressure setting to IMB
     if end == True and validate == True:
         putOTPD(channel, otpd)
         print("OTPD set to "+otpd)
         return True
     else:
         print("OTPD setting error")
         return False

def putPUTO(channel, timeout):
    timeout = str(timeout)
    channel = str(channel)
    client.put("/fc/"+channel+"/cset/pu/PUTO", timeout)

def getPUTO(channel):
    channel = str(channel)
    response = client.get("/fc/"+channel+"/cset/pu/PUTO")
    return int(response.payload) 

def putPCTO(channel, timeout):
    timeout = str(timeout)
    channel = str(channel)
    client.put("/fc/"+channel+"/cset/pu/PCTO", timeout)

def getPCTO(channel):
    channel = str(channel)
    response = client.get("/fc/"+channel+"/cset/pu/PCTO")
    return int(response.payload) 

def putESTO(channel,timeout):
    channel = str(channel)
    client.put("/s/" + channel + "/va/ESTO", str(timeout))    

def getESTO(channel):
    channel = str(channel)
    response = client.get("/s/" + channel + "/va/ESTO")    
    return int(response.payload) 

def putSSTO(channel,timeout):
    channel = str(channel)
    client.put("/s/" + channel + "/va/SSTO", str(timeout))    

def getSSTO(channel):
    channel = str(channel)
    response = client.get("/s/" + channel + "/va/SSTO")    
    return int(response.payload) 

def putIP2Mode(channel,mode):
    channel = str(channel)
    client.put("/s/"+channel+"/va/IP2MODE", str(mode))    

def getIP2Mode(channel):
    channel = str(channel)
    response = client.get("/s/"+channel+"/va/IP2MODE")    
    return int(response.payload) 



###Actuators##

def getOutletPressure(channel):
    try:    
        response = client.get("/pr/OTPS?uc="+str(channel))
        return int(response.payload)
    except AttributeError:
        return False
        
def getInletPressure(channel):
    try:
        response = client.get("/pr/ITPS?uc="+str(channel))
        return int(response.payload)
    except AttributeError:
        return False
        
def getActuatorStatus(channel):
     channel = str(channel)
     response = client.get("/actuator/state?uc="+channel)
     return response.payload

def getOutletFloat(channel):
    channel = str(channel)
    floatOutlet = getActuatorStatus(channel).split('F')[1][0:1]
    return floatOutlet

def getInletFloat(channel):
    channel = str(channel)
    floatInlet = getActuatorStatus(channel).split('F')[1][2:3]
    return floatInlet

def getInletPressureAS(channel):
    channel = str(channel)
    splitP = getActuatorStatus(channel).split('P')[1]
    splitComma = splitP.split(",")
    return splitComma[0] # Returns pressure as a string

def getOutletPressureAS(channel):
    channel = str(channel)
    splitP = getActuatorStatus(channel).split('P')[1]
    splitT = splitP.split("T")[0]
    splitComma = splitT.split(",")
    return splitComma[1] # Returns pressure as a string

def getIP1state(channel):
    channel = str(channel)
    split = getActuatorStatus(channel).split('I')[1].split('V')[0][0:1]
    return int(split) #Returns 1 or 0 as an integer

def getIP2state(channel):
    channel = str(channel)
    split = getActuatorStatus(channel).split('I')[1].split('V')[0][1:2]
    return int(split) #Returns 1 or 0 as an integer

def getVP1state(channel):
    channel = str(channel)
    split = getActuatorStatus(channel).split('V')[1].split('B')[0][0:1]
    return int(split) #Returns 1 or 0 as an integer

def getVP2state(channel):
    channel = str(channel)
    split = getActuatorStatus(channel).split('V')[1].split('B')[0][1:2]
    return int(split) #Returns 1 or 0 as an integer

def getS1state(channel):
    channel = str(channel)
    split = getActuatorStatus(channel).split('S')[1].split('H')[0][0:1]
    return int(split) #Returns 1 or 0 as an integer

def getS2state(channel):
    channel = str(channel)
    split = getActuatorStatus(channel).split('S')[1].split('H')[0][1:2]
    return int(split) #Returns 1 or 0 as an integer

def getS3state(channel):
    channel = str(channel)
    split = getActuatorStatus(channel).split('S')[1].split('H')[0][2:3]
    return int(split) #Returns 1 or 0 as an integer

def getS4state(channel):
    channel = str(channel)
    split = getActuatorStatus(channel).split('S')[1].split('H')[0][3:4]
    return int(split) #Returns 1 or 0 as an integer

def getS5state(channel):
    channel = str(channel)
    split = getActuatorStatus(channel).split('S')[1].split('H')[0][4:5]
    return int(split) #Returns 1 or 0 as an integer

def disableHeater(channel):
    channel = str(channel)
    client.put("/heater/enabled?uc="+channel, "0")
    client.put("/heater/sensor?uc="+channel, "0")

def getTemperature(channel):
    channel = str(channel)
    response = client.get("/heater/temperature?uc="+channel)
    return int(response.payload)/10

def getHeaterTemperatureTarget(channel):
    channel = str(channel)
    response = client.get("/heater/target?uc="+channel)
    return int(response.payload)/10

def putHeaterTemperatureTarget(channel, temperature):
    temperature = str(int(temperature) * 10)
    channel = str(channel)
    client.put("/heater/target?uc="+channel, temperature)

def getHeaterState(channel):
    channel = str(channel)
    response = client.get("/heater/enabled?uc="+channel)
    return int(response.payload)
    


# Actuator Monitor

##	CAS_INK_PUMP_1 = 0,
##	CAS_INK_PUMP_2 = 1,
##	CAS_VACUUM_PUMP1 = 2,
##	CAS_VACUUM_PUMP2 = 3,
##	CAS_HTB_HEATER_1 = 4,
##	CAS_HTB_HEATER_2 = 5,
##	CAS_HTB_SOLENOID_1 = 6,
##	CAS_HTB_SOLENOID_2 = 7,
##	CAS_IMB_SOLENOID_1 = 8,
##	CAS_IMB_SOLENOID_2 = 9,
##	CAS_IMB_SOLENOID_5 = 10,
##	CAS_ACTUATORS = 11,
##	CAS_ACTUATOR_UNKNOWN = 12
##



def getActuatorDutycyleSMAPeriod(act, state, dcset):
    act = str (act)
    state = str( state)
    dcset = str(dcset)    
    response = client.get("/actuator/"+act+"/"+state+"/smaperiod/"+dcset)
    return response.payload

def getActuatorDutycyle(act, state, dcset):
    act = str (act)
    state = str( state)
    dcset = str(dcset)    
    response = client.get("/actuator/"+act+"/"+state+"/dutycyclesma/"+dcset)
    return response.payload

def getActuatorControlState(act):
    act = str (act)    
    response = client.get("/actuator/"+act+"/controlstate")
    statestr = response.payload
    statestr = statestr.split(",", 1)
    return statestr[0]


def getActuatorCycles(act, state):
    act = str (act)
    state = str (state)
    response = client.get("/actuator/"+act+"/"+ state +"/cycles")
    return response.payload

def getActuatorCycles10sec(act, state):
    act = str (act)
    state = str (state)    
    response = client.get("/actuator/"+act+"/"+ state +"/cycles10sec")
    return response.payload

def getActuatorCycles1min(act, state):
    act = str (act)
    state = str (state)    
    response = client.get("/actuator/"+act+"/"+ state +"/cycles1min")
    return response.payload


def getInkPumpDC(channel, pump):
    act = getInkPumpID(channel, pump)
    state = getActuatorControlState(act)
    line1 = ("Act = " + str(act) + " State = " + str(state))
    line2 = ("Total Cycles = " + str (getActuatorCycles(act, state)))
    line3 = ("Cycles in last minute = " + str (getActuatorCycles1min(act, state)))
    line4 = ("Cycles in last 10 sec = " + str (getActuatorCycles10sec(act, state)))
    line5 = ("DC Set 1 = " + str(getActuatorDutycyle(act, state, 1)))
    line6 = ("DC Set 2 = " + str(getActuatorDutycyle(act, state, 2)))
    print(line1, line2, line3, line4, line5, line6)

def getInkPumpID(channel, pump):
    if pump == 1:
        return getActuatorID(channel,0)
    if pump == 2:
        return getActuatorID(channel,1)

def getActuatorID(channel, act):
    channel = str(channel)
    act = str(act)
    response = client.get("/actuator/"+channel+"/"+act+"/id")    
    return response.payload

def getActuatorName(channel):
    channel = str(channel)    
    response = client.get("/actuator/"+channel+"/name")    
    return response.payload