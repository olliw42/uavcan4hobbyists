#!/usr/bin/env python3
'''
OlliW 25.Mar.2018
'''


#---------------------------------------------------------
# ArduPilot constants
#---------------------------------------------------------

cAPVEHICLETPYE_XQUAD = 0



   
    
#---------------------------------------------------------
# ArduPilot motor maping stuff
#---------------------------------------------------------

ap_vehicle_type = None

#map the motors to the ArduPilot indices
ap_motor_esc_map = {}
ap_motor_esc_map_keys = []

    
def _setAPXQuadMotorEscMap():
    global ap_motor_esc_map
    global ap_motor_esc_map_keys
    ap_motor_esc_map = { 'A': 0, 'B': 3, 'C': 1, 'D': 2 }
    ap_motor_esc_map_keys = ap_motor_esc_map.keys()

    
def setAPMotorEscMap(vehicle=cAPVEHICLETPYE_XQUAD):
    #only x quad currently
    _setAPXQuadMotorEscMap()
    

def _printAPXQuadMotorConfiguration():
    print(' ->       <- ')
    print(' D         A ')
    print('   *     *   ')
    print('     * *     ')
    print('     * *     ')
    print('   *     *   ')
    print(' C         B ')
    print(' ->       <- ')





def apInit(vehicle=cAPVEHICLETPYE_XQUAD):
    ap_vehicle_type = vehicle
    setAPMotorEscMap(vehicle)

    
def apVehicleTypeStr():
    #only x quad currently
    return 'XQUAD'
    
    
def apMotorNumber():
    #only x quad currently
    # could/should be determined from length of ap_motor_esc_map
    return int(4)


def apMotorEscMap():
    return ap_motor_esc_map

    
def printAPMotorConfiguration():
    #only x quad currently
    _printAPXQuadMotorConfiguration()
            
            
