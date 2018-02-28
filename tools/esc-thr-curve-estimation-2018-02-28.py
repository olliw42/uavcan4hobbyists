#!/usr/bin/env python3
'''
measurement of rpm vs pwm and I vs pwm, using a UC4H ESC KISS32A node
=> calculation of estimated thrust vs pwm
=> fit to poly function to estimate MOT_THST_EXPO parameter

OlliW 28.Feb.2018
'''

#based on the example here: http://uavcan.org/Implementations/Pyuavcan/Examples/ESC_throttle_control/
#see https://groups.google.com/forum/#!topic/uavcan/cz7UBGZTdF8 for how to get things working on Win
# thx, Pavel !

import uavcan, time, math
import msvcrt, sys
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit


# class to record data in repeated up/down sweeps
cSTATUS_INITIALIZEMOTOR = 0
cSTATUS_INITIALRAMP = 1
cSTATUS_RECORDINGRAMP = 2
cSTATUS_ABORTRAMP = 3
cSTATUS_EXIT = 4

class cRecord:

    def __init__(self,_node,_escIndex,_fig=None,_ax=None,_ax2=None):
        self.node = _node
        self.escIndex = _escIndex
        
        self.status = cSTATUS_INITIALIZEMOTOR
        self.status_cnt = 20 #startup initialization time, 1 sec
        self.setpoint = int(0)
        self.direction_up = True
        
        if self.escIndex > 3:
            self.emptyCommands = [0]*(self.escIndex+1) #this adapts to the number of ESCs
        else:    
            self.emptyCommands = [0,0,0,0] #assume at minimum 4 ESCs
            
        self.pwm = []    
        self.rpm = []    
        self.current = []    
        self.fig = _fig
        self.ax = _ax
        self.ax2 = _ax2

    def broadcastEscSetpoint(self):
        if self.status == cSTATUS_INITIALIZEMOTOR:
            self.setpoint = int(0)
            self.status_cnt -= 1
            if self.status_cnt <= 0: 
                self.direction_up = True
                self.status = cSTATUS_INITIALRAMP #cSTATUS_RECORDINGRAMP
        elif self.status == cSTATUS_INITIALRAMP:
            if self.direction_up:
                self.setpoint += 20 
                if self.setpoint >= 1500: self.direction_up = False
            else:
                self.setpoint -= 20
                if self.setpoint <= 100: 
                    self.direction_up = True
                    self.status = cSTATUS_RECORDINGRAMP
        elif self.status == cSTATUS_RECORDINGRAMP or self.status == cSTATUS_ABORTRAMP:
            if self.direction_up:
                self.setpoint += 20 
                if self.setpoint >= 8100: self.direction_up = False
            else:
                self.setpoint -= 20
                if self.setpoint <= 100: self.direction_up = True
            if self.status == cSTATUS_ABORTRAMP:
                self.direction_up = False # 'quick' abort, comment out to have complete sweeps
                if self.setpoint <= 101:
                    self.setpoint = int(0)
                    self.status = cSTATUS_EXIT
    
        commands = self.emptyCommands
        commands[self.escIndex] = self.setpoint
        message = uavcan.equipment.esc.RawCommand(cmd=commands)
        self.node.broadcast(message)
    
    def printEscStatus(self,msg):
        if self.status >= cSTATUS_RECORDINGRAMP and not math.isnan(msg.message.rpm) and not math.isnan(msg.message.current):
            self.pwm.append(self.setpoint)
            self.rpm.append(msg.message.rpm)
            self.current.append(msg.message.current)
            
        if self.status >= cSTATUS_ABORTRAMP:
            print('  ',self.setpoint,', ',msg.message.rpm,'rpm, ',msg.message.current,'A','STOP')
        else:
            print('  ',self.setpoint,', ',msg.message.rpm,'rpm, ',msg.message.current,'A')
            
        if self.fig:
            self.ax.clear()
            self.ax.plot(self.pwm,self.rpm,'bo')
            self.ax2.clear()
            self.ax2.plot(self.pwm,self.current,'r')
            self.fig.canvas.draw()
            time.sleep(0.01)
        #print(uavcan.to_yaml(msg))
        
    def run(self):
        hPeriodic = self.node.periodic(0.05, self.broadcastEscSetpoint)
        hEscStatus = self.node.add_handler(uavcan.equipment.esc.Status, self.printEscStatus)
        while self.status < cSTATUS_EXIT:
            try:
                self.node.spin(1)
                if msvcrt.kbhit():
                    msvcrt.getch()
                    self.status = cSTATUS_ABORTRAMP
            #except UAVCANException as ex: #leads to NameError: name is not defined ???
            #    print('NODE ERROR:', ex)            
            except KeyboardInterrupt:
                sys.exit(0)
        hEscStatus.remove()
        hPeriodic.remove()

        
def createFig0():
    #plt.ion()
    fig0 = plt.figure(0)
    
    ax01 = fig0.add_subplot(111)
    ax01.plot([], [], 'bo')
    ax01.set_xlabel('pwm') #doesn't work, why?
    ax01.set_ylabel('rpm') #doesn't work, why?
    ax01.tick_params( axis='y', colors='b' )
    ax01.relim() 
    ax01.autoscale_view(True,True,True)
    
    ax02 = ax01.twinx()
    ax02.plot([], [], 'r')
    ax02.set_ylabel('current (A)') #doesn't work, why?
    ax02.tick_params( axis='y', colors='r' )
    ax02.relim() 
    ax02.autoscale_view(True,True,True)
    
    fig0.tight_layout()
    fig0.canvas.draw()
    
    return fig0, ax01, ax02


'''
Theory:
    Prop:
    S = c_S rho omega^2 D^4
    P_M = c_P rho omega^3 D^5
    P_M = M omega
    => 
    S^3 = pi/2 rho D^2 xi^2 P_M^2
    
    Motor:
    M \approx k I
    =>
    S^3 \approx pi/2 rho D^2 xi^2 k^2 I^2 omega^2 = c^3 (I omega)^2
    =>
    S(pwm) \approx c [I(pwm) omega(pwm)]^(2/3)
'''
def calculateThrust(record):
    pwm_scaled = []
    thrust = []
    for i in range(len(record.pwm)):
        pwm = record.pwm[i]
        pwm_scaled.append( pwm/8192.0 )
        current = record.current[i]
        omega = record.rpm[i] #we don't ned to convert to proper units, since only the exponent in the algebraic function is relevant
        thrust.append( math.pow(current*omega,2.0/3.0) )
        
    return pwm_scaled, thrust

    
def createFig1(pwm_scaled,thrust):
    fig1 = plt.figure(1)
    ax11 = fig1.add_subplot(111)
    ax11.plot( pwm_scaled, thrust, 'bo')
    ax11.plot( pwm_scaled, thrust, 'b')
    ax11.set_xlabel('scaled pwm')
    ax11.set_ylabel('estimated thrust (a.u.)')    
    
    fig1.canvas.draw()
    
    
def calculateNormalizedThrustCurve(_pwm_scaled,_thrust,spin_min=0.15,spin_max=0.95):
    pwm_norm = []
    thrust_norm = []
    thrust_max = 0.0
    thrust_min = 1.0e10
    for i in range(len(_pwm_scaled)):
        pwm = _pwm_scaled[i]
        if (pwm < spin_min) or (pwm > spin_max): continue #only search in the allowed range
        thrust = _thrust[i]
        if thrust > thrust_max: thrust_max = thrust
        if thrust < thrust_min: thrust_min = thrust
    
    for i in range(len(_pwm_scaled)):
        pwm = _pwm_scaled[i]
        if (pwm < spin_min) or (pwm > spin_max): continue #only accept the allowed range
        pwm_n = pwm # is identical to scaled pwm
        pwm_norm.append( pwm_n )
        thrust = _thrust[i]
        thrust_n = (thrust - thrust_min)/(thrust_max - thrust_min) #must be ranged such that it 0,1 at MOT_SPIN_MIN,MOT_SPIN_MAX
        thrust_norm.append( thrust_n )
        
    return pwm_norm, thrust_norm

    
def createFig23(pwm_norm,thrust_norm,fit=None):
    if fit:
        fig = plt.figure(3)
    else:    
        fig = plt.figure(2)
    ax = fig.add_subplot(111)
    ax.plot( pwm_norm, thrust_norm, 'bo')
    ax.plot( pwm_norm, thrust_norm, 'b')
    ax.set_xlabel('normalzed pwm')
    ax.set_ylabel('normalized thrust')
    if fit:
        ax.plot( pwm_norm, fit, 'ro')
    ax.set_xlim([0.0,1.0])    
    ax.set_ylim([0.0,1.0])    
    fig.canvas.draw()
    
'''
Theory
    there is info here http://ardupilot.org/copter/docs/motor-thrust-scaling.html
    a more detailed account of what the current code in ArduCopter is doing,
    has been worked out here https://discuss.ardupilot.org/t/using-measured-mot-thst-expo-what-improvement-can-one-expect/26172/23
    
    The math doen in ArduCopter can be summarized as follows:
    // converts thrust_in = [0…1] to throttle_ratio = [0…1]
    throttle_ratio =
        [ -(1.0-expo) + sqrt{ (1.0-expo)*(1.0-expo) + 4.0 * expo * lift_max * thrust_in } ]
        /
        [ 2.0 * expo * batt_voltage_filt ]
    // converts throttle_ratio = [0…1] to X = [spin_min…spin_max]
    X = spin_min + (spin_max - spin_min) * throttle_ratio(thrust_in)
    // converts X = [0…1] to pwm = [pwm_min…pwm_max]
    thrust_to_pwm = pwm_min + (pwm_max - pwm_min) * X    
    =>
    X_norm = (X - spin_min) / (spin_max - spin_min)    
    thrust_in = (1-expo) * X_norm + expo * X_norm^2
'''

fitfunc_x_min = 0.0
fitfunc_x_max = 1.0

def setFitFuncMinMax(spin_min=0.15,spin_max=0.95):
    global fitfunc_x_min
    global fitfunc_x_max
    fitfunc_x_min = spin_min
    fitfunc_x_max = spin_max

def fitFunc(x, a):
    x_n = (x - fitfunc_x_min)/(fitfunc_x_max - fitfunc_x_min)
    return (1.0-a) * x_n + a * x_n*x_n
        

def fitNormalizedThurstCurve(pwm_norm,thrust_norm,_min, _max):
    '''
    thrust_norm = []
    for i in range(len(pwm_norm)): thrust_norm.append( func(pwm_norm[i],0.8) )        
    '''
    
    xdata = np.array(pwm_norm)
    ydata = np.array(thrust_norm)
    
    setFitFuncMinMax(_min, _max)
    
    popt, pcov = curve_fit(fitFunc, xdata, ydata, p0=(0.5))    
    return popt[0], pcov[0][0]
    
        
def createNode(com):
    node = uavcan.make_node(com, node_id=126, bitrate=1000000, baudrate=1000000)

    node_monitor = uavcan.app.node_monitor.NodeMonitor(node)

#    dynamic_node_id_allocator = uavcan.app.dynamic_node_id.CentralizedServer(node, node_monitor)
#    while len(dynamic_node_id_allocator.get_allocation_table()) <= 1:
#        print('Waiting for other nodes to become online...')
#        node.spin(timeout=1)
        
    while len(node_monitor.get_all_node_id()) < 1:
        print('Waiting for other nodes to become online...')
        node.spin(timeout=1)
        
    all_node_ids = list(node_monitor.get_all_node_id())
    print( '\nDetected Node IDs',all_node_ids)
    print( 'Node ID in use',all_node_ids[0],)
    node_dict = node_monitor.get(all_node_ids[0]) #momentarily, always use the first, one shouldk use an ESC detection scheme as in the examples
    
    return node;

    
if __name__ == '__main__':

    node = createNode('COM38');
    
    escIndex = 3

    print('\nsave files at end (y/n)?')
    saveFiles = False
    if msvcrt.getch() != 'n': saveFiles = True
    
    print('\nPress keyboard to START... ')
    while True:
        try:
            if msvcrt.kbhit():
                msvcrt.getche()
                break
        except KeyboardInterrupt:
            sys.exit(0)

    print('\nSTART Data recording... ')
    fig0, ax01, ax02 = createFig0()
    plt.show(block=False)
    record = cRecord(node, escIndex, fig0, ax01, ax02) #enter the desired esc index
    record.run()
    print('DONE')

    if len(record.pwm) > 2:
        print('calculating thrust curve... ')
        pwm_scaled, thrust = calculateThrust(record)
        #createFig1(pwm_scaled, thrust)
        print('DONE')
        
        MOT_SPIN_MIN = 0.15
        MOT_SPIN_MAX = 0.95
        
        print('calculating normalized thrust curve... ')
        pwm_norm, thrust_norm = calculateNormalizedThrustCurve(pwm_scaled, thrust, MOT_SPIN_MIN, MOT_SPIN_MAX)
        createFig23(pwm_norm, thrust_norm)
        print('DONE')
        
        print('fitting normalized thrust curve... ')
        popt, pcov = fitNormalizedThurstCurve(pwm_norm, thrust_norm, MOT_SPIN_MIN, MOT_SPIN_MAX) #       popt, pcov = 0.5,0.0
        print(popt,pcov)
        fit = []
        for i in range(len(pwm_norm)): fit.append( fitFunc(pwm_norm[i],popt) )        
        createFig23(pwm_norm, thrust_norm, fit)
        print('DONE')
                
        if saveFiles:
            fname = 'esc-thr-curve.'+str(escIndex)
            F = open( fname+'.raw.dat', 'w')
            F.write( 'i\tpwm\tpwm_scaled\trpm\tcurrent\tthrust\n' )
            for i in range(len(record.pwm)):
                line = ''
                line += str(i) + '\t'
                line += str(record.pwm[i]) + '\t'
                line += '{:.6f}'.format(pwm_scaled[i]) + '\t'
                line += '{:.6f}'.format(record.rpm[i]) + '\t'
                line += '{:.6f}'.format(record.current[i]) + '\t'
                line += '{:.6f}'.format(thrust[i]) + '\n'
                F.write( line )
            F.close()
    
            F = open( fname+'.normalized.dat', 'w')
            F.write( 'i\tpwm_norm\tthrust_norm\tfit\n' )
            for i in range(len(pwm_norm)):
                line = ''
                line += str(i) + '\t'
                line += '{:.6f}'.format(pwm_norm[i]) + '\t'
                line += '{:.6f}'.format(thrust_norm[i]) + '\t'
                line += '{:.6f}'.format(fit[i]) + '\n'
                F.write( line )
            F.close()
    
    plt.show(block=True)
    
