#!/usr/bin/env python3
'''
OlliW 28.Feb.2018
Script for half-automated setup of UC4H ESC nodes
'''

version_str = '3.Mar.2018 v001'


#---------------------------------------------------------
# user adjustable parameters
#---------------------------------------------------------

slcan_com = 'COM38'
    
number_of_escs_per_escnode = 1

motor_spin_inpercent = 10



#based on the example here: http://uavcan.org/Implementations/Pyuavcan/Examples/ESC_throttle_control/
#see https://groups.google.com/forum/#!topic/uavcan/cz7UBGZTdF8 for how to get things working on Win
# thx, Pavel !

import uavcan, time, math
import msvcrt, sys
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit


#---------------------------------------------------------
# keyboard convenience functions
#---------------------------------------------------------

def clearKeys():
    while msvcrt.kbhit(): msvcrt.getch() #clear all chars in the buffer
    

def pressKeyboardToContinue(node=None,force=True):
    print('\npress any key to continue... ')
    if force: clearKeys() 
    while True:
        try:
            if node: node.spin(0.1)
            if msvcrt.kbhit():
                msvcrt.getch()
                break
        except KeyboardInterrupt:
            sys.exit(0)

            
def pressYesNo(node=None,force=True):
    if force: clearKeys() 
    while True:
        try:
            if node: node.spin(0.1)
            if msvcrt.kbhit():
                c = msvcrt.getch()
                if (c == b'y') or (c == b'Y'): return True
                return False
                #break
        except KeyboardInterrupt:
            sys.exit(0)
    return False        

    
def getKey(node=None,force=False):
    if force: clearKeys() 
    while True:
        try:
            if node: node.spin(0.1)
            if msvcrt.kbhit():
                c = msvcrt.getch() #sometimes Python is really unnessecarily silly
                try:
                    cc = c.decode("utf-8")
                except:
                    cc = '\0'
                return cc
        except KeyboardInterrupt:
            sys.exit(0)
    return '\0'

    
#---------------------------------------------------------
# basic UAVCAN support functions
#---------------------------------------------------------
    
def get_parameter_byindexorname(node,target_node_id,indnam,return_yaml=False,force=True):

    response_received = False
    is_valid = False
    param_dict = {}
    param_yaml = {}
    is_name = type(indnam) is str
    
    def param_getset_response(event):
        nonlocal response_received
        nonlocal is_valid
        nonlocal param_dict
        nonlocal return_yaml
        nonlocal param_yaml
        if not event:
            raise Exception('Request timed out')
        response_received = True
        is_valid = not hasattr(event.transfer.payload.value,'empty')
        if is_valid:
            #print(event)
            #print(uavcan.to_yaml(event))
            if return_yaml:
                param_yaml = uavcan.to_yaml(event)
            else:
                param_dict['name'] = str(event.transfer.payload.name)
                if hasattr(event.transfer.payload.value,'integer_value'):
                    param_dict['value'] = event.transfer.payload.value.integer_value
                if hasattr(event.transfer.payload.value,'real_value'):
                    param_dict['value'] = event.transfer.payload.value.real_value
    
    tmo_time = time.time() + 5.0
    while not is_valid:
        if time.time() > tmo_time: break
        response_received = False
        if is_name:
            node.request(uavcan.protocol.param.GetSet.Request(
                        index = 0,
                        #value = uavcan.protocol.param.Value(empty=uavcan.protocol.param.Empty()),
                        name = str(indnam)
                    ),
                    target_node_id,
                    param_getset_response
                )
        else:
            node.request(uavcan.protocol.param.GetSet.Request(
                        index = int(indnam),
                        #value = uavcan.protocol.param.Value(empty=uavcan.protocol.param.Empty()),
                        #name = ''
                    ),
                    target_node_id,
                    param_getset_response
                )
        while not response_received:
            try:
                node.spin(0.25)
            except:
                break
            if time.time() > tmo_time: break
    
    if return_yaml:
        return is_valid, param_yaml
    else:    
        return is_valid, param_dict
        

def get_parameters(node,target_node_id):
    for i in range(100): #don't accept more than 100 parameters
        res,param = get_parameter_byindexorname(node,target_node_id,i)
        if not res: return
        print(param['name'], ':', param['value'])


def set_parameter_byindexorname(node,target_node_id,indnam,intfloatvalue):
    response_received = False
    is_valid = False
    is_name = type(indnam) is str
    is_float = type(intfloatvalue) is float
    
    if is_float:
        val = uavcan.protocol.param.Value(real_value=int(intfloatvalue))
    else:
        val = uavcan.protocol.param.Value(integer_value=int(intfloatvalue))           
    
    def param_getset_response(event):
        nonlocal response_received
        nonlocal is_valid
        if not event:
            raise Exception('Request timed out')
        response_received = True
        is_valid = not hasattr(event.transfer.payload.value,'empty')
        if is_valid:
            #print(event)
            #print(uavcan.to_yaml(event))
            is_valid = False
            if hasattr(event.transfer.payload.value,'integer_value'):
                if not is_float and (event.transfer.payload.value.integer_value == int(intfloatvalue)):
                    is_valid = True
            if hasattr(event.transfer.payload.value,'real_value'):
                if is_float and (event.transfer.payload.value.real_value == float(intfloatvalue)):
                    is_valid = True

    tmo_time = time.time() + 5.0
    while not is_valid:
        if time.time() > tmo_time: break
        response_received = False
        if is_name:
            node.request(uavcan.protocol.param.GetSet.Request(
                        index = 0,
                        value = val,
                        name = str(indnam)
                    ),
                    target_node_id,
                    param_getset_response
                )
        else:
            node.request(uavcan.protocol.param.GetSet.Request(
                        index = int(indnam),
                        value = val,
                        #name = ''
                    ),
                    target_node_id,
                    param_getset_response
                )
        while not response_received:
            try:
                node.spin(0.25)
            except:
                break
            if time.time() > tmo_time: break
            
    return is_valid


def execute_opcode(node,target_node_id,intopcode=0): #0: OPCODE_SAVE  1: OPCODE_ERASE
    response_received = False
    is_valid = False

    if intopcode == 1:
        opcode = uavcan.protocol.param.ExecuteOpcode.Request().OPCODE_ERASE
    else:    
        opcode = uavcan.protocol.param.ExecuteOpcode.Request().OPCODE_SAVE
    
    def param_executeopcode_response(event):
        nonlocal response_received
        nonlocal is_valid
        if not event:
            raise Exception('Request timed out')
        response_received = True
        if not event.response.ok:
            raise Exception('Param opcode execution rejected\n' + uavcan.to_yaml(event))
        else:
            is_valid = True

    tmo_time = time.time() + 5.0
    while not is_valid:
        if time.time() > tmo_time: break
        response_received = False
        node.request(uavcan.protocol.param.ExecuteOpcode.Request(
                        opcode = opcode
                    ),
                    target_node_id,
                    param_executeopcode_response
                )
        while not response_received:
            try:
                node.spin(0.25)
            except:
                break
            if time.time() > tmo_time: break
    
    return is_valid
    
    
def restart_node(node,target_node_id):
    response_received = False
    is_valid = False

    def response_func(event):
        nonlocal response_received
        nonlocal is_valid
        if not event:
            raise Exception('Request timed out')
        response_received = True
        if not event.response.ok:
            raise Exception('Param opcode execution rejected\n' + uavcan.to_yaml(event))
        else:
            is_valid = True

    tmo_time = time.time() + 5.0
    while not is_valid:
        if time.time() > tmo_time: break
        response_received = False
        node.request(uavcan.protocol.RestartNode.Request(
                        magic_number = uavcan.protocol.RestartNode.Request().MAGIC_NUMBER
                    ),
                    target_node_id,
                    response_func
                )
        while not response_received:
            try:
                node.spin(0.25)
            except:
                break
            if time.time() > tmo_time: break
    
    return is_valid
    
    
#---------------------------------------------------------
# node discovery and detection functions
#---------------------------------------------------------

def waitForAllNodes(node_monitor,node):
    
    detected_number_of_nodes = 0
    detect_cnt = 3 #look 3 seconds for changes in the number of nodes
    while detect_cnt or not detected_number_of_nodes:
        print('Waiting for all nodes to become online...')
        node.spin(timeout=1)
        n = len(node_monitor.get_all_node_id())
        if n > 0:
            detect_cnt -= 1
            if n > detected_number_of_nodes:
                detected_number_of_nodes = n
                detect_cnt = 3
    
        
def createNode(com):
    node = uavcan.make_node(com, node_id=126, bitrate=1000000, baudrate=1000000)

    node_monitor = uavcan.app.node_monitor.NodeMonitor(node)

#    dynamic_node_id_allocator = uavcan.app.dynamic_node_id.CentralizedServer(node, node_monitor)
#    while len(dynamic_node_id_allocator.get_allocation_table()) <= 1:
#        print('Waiting for other nodes to become online...')
#        node.spin(timeout=1)
    
    waitForAllNodes(node_monitor,node)
        
    return node_monitor, node

    
#from: http://uavcan.org/Implementations/Pyuavcan/Examples/Automated_ESC_enumeration/
def detect_esc_nodes_bymessage(node):
    esc_nodes = set()
    handle = node.add_handler(uavcan.equipment.esc.Status, lambda event: esc_nodes.add(event.transfer.source_node_id))
    try:
        node.spin(timeout=3)            # Collecting ESC status messages, thus determining which nodes are ESC
    finally:
        handle.remove()

    return esc_nodes

    
def detect_uc4h_nodes_byname(node_monitor):
    esc_nodes = set()
    powerbrick_nodes = set()
    all_node_ids = sorted(list(node_monitor.get_all_node_id()))
    for id in all_node_ids:
        n = str(node_monitor.get(id).info.name)
        print(n)
        if '-esc-' in n: esc_nodes.add(id)
        if '-powerbrick-' in n: powerbrick_nodes.add(id)
        
    return esc_nodes, powerbrick_nodes
    
        
def detect_all_uc4h_escs(node_monitor,node):
    esc_node_ids_set = set()
    all_node_ids = sorted(list(node_monitor.get_all_node_id()))
    for id in all_node_ids:
        n = str(node_monitor.get(id).info.name)
        if 'uc4h-esc' in n: esc_node_ids_set.add(id)
    return sorted(list(esc_node_ids_set))

    
#---------------------------------------------------------
# UC4H ESC specific functions
#---------------------------------------------------------
    
def get_uc4h_esc_indicies(node, esc_node_ids):
    #go through all uc4h escs and extract their supported indices     
    esc_list = []
    esc_index_set = set()
    for id in esc_node_ids:
        print('  get esc indices for node',id)

        res, OutAMode = get_parameter_byindexorname(node,id,'OutA Mode')
        if not res: return [],[]
        res, OutBMode = get_parameter_byindexorname(node,id,'OutB Mode')
        if not res: return [],[]
        res, OutCMode = get_parameter_byindexorname(node,id,'OutC Mode')
        if not res: return [],[]
        
        res, OutA1Index = get_parameter_byindexorname(node,id,'OutA1 Index')
        if not res: return [],[]
        res, OutA2Index = get_parameter_byindexorname(node,id,'OutA2 Index')
        if not res: return [],[]

        res, OutB1Index = get_parameter_byindexorname(node,id,'OutB1 Index')
        if not res: return [],[]
        res, OutB2Index = get_parameter_byindexorname(node,id,'OutB2 Index')
        if not res: return [],[]
        
        res, OutC1Index = get_parameter_byindexorname(node,id,'OutC1 Index')
        if not res: return [],[]
        res, OutC2Index = get_parameter_byindexorname(node,id,'OutC2 Index')
        if not res: return [],[]
        
        #we have now all info we need
        if OutAMode['value'] > 0:
            if OutA1Index['value'] > -1: 
                esc_list.append( {'esc_index': OutA1Index['value'], 'node_id': id} )
                esc_index_set.add(OutA1Index['value'])
            if OutA2Index['value'] > -1: 
                esc_list.append( {'esc_index': OutA2Index['value'], 'node_id': id} )
                esc_index_set.add(OutA2Index['value'])
        if OutBMode['value'] > 0:
            if OutB1Index['value'] > -1: 
                esc_list.append( {'esc_index': OutB1Index['value'], 'node_id': id} )
                esc_index_set.add(OutB1Index['value'])
            if OutB2Index['value'] > -1: 
                esc_list.append( {'esc_index': OutB2Index['value'], 'node_id': id} )
                esc_index_set.add(OutB2Index['value'])
        if OutCMode['value'] > 0:
            if OutC1Index['value'] > -1: 
                esc_list.append( {'esc_index': OutC1Index['value'], 'node_id': id} )
                esc_index_set.add(OutC1Index['value'])
            if OutC2Index['value'] > -1: 
                esc_list.append( {'esc_index': OutC2Index['value'], 'node_id': id} )
                esc_index_set.add(OutC2Index['value'])
        
    return list(esc_index_set), esc_list

    
def set_uc4h_esc_indicies(node, esc_node_ids, esc_indexes):
    #this are the indices which are now going to be written into the nodes
    
    #we assume here that esc_node_ids and esc_index are correctly set up !!!
    number_of_escs_per_escnode = int(len(esc_indexes) / len(esc_node_ids))
    
    current_index_pos = 0 #this is the 'pointer' into the esc_indexes list
    for id in esc_node_ids:
        #offer a nice printout
        s = '['
        for i in range(number_of_escs_per_escnode):
            s += str(esc_indexes[current_index_pos+i]) + ','
        s = s[:-1] + ']'
        print('  set esc indices for node',id,'to',s)

        #this could be done more elegantly, but let's do it stupidly
        if number_of_escs_per_escnode > 0:
            res = set_parameter_byindexorname(node, id, 'OutA Mode', 3) #sets DSHOT
            res = set_parameter_byindexorname(node, id, 'OutA1 Index', esc_indexes[current_index_pos])
            current_index_pos += 1
        else:
            res = set_parameter_byindexorname(node, id, 'OutA Mode', 0) #disable
            res = set_parameter_byindexorname(node, id, 'OutA1 Index', -1)
            
        if number_of_escs_per_escnode > 1:
            res = set_parameter_byindexorname(node, id, 'OutA2 Index', esc_indexes[current_index_pos])
            current_index_pos += 1
        else:
            res = set_parameter_byindexorname(node, id, 'OutA2 Index', -1)
         
        if number_of_escs_per_escnode > 2:
            res = set_parameter_byindexorname(node, id, 'OutB Mode', 3) #sets DSHOT
            res = set_parameter_byindexorname(node, id, 'OutB1 Index', esc_indexes[current_index_pos])
            current_index_pos += 1
        else:
            res = set_parameter_byindexorname(node, id, 'OutB Mode', 0) #disable
            res = set_parameter_byindexorname(node, id, 'OutB1 Index', -1)
            
        if number_of_escs_per_escnode > 3:
            res = set_parameter_byindexorname(node, id, 'OutB2 Index', esc_indexes[current_index_pos])
            current_index_pos += 1
        else:
            res = set_parameter_byindexorname(node, id, 'OutB2 Index', -1)

        if number_of_escs_per_escnode > 4:
            res = set_parameter_byindexorname(node, id, 'OutC Mode', 3) #sets DSHOT
            res = set_parameter_byindexorname(node, id, 'OutC1 Index', esc_indexes[current_index_pos])
            current_index_pos += 1
        else:
            res = set_parameter_byindexorname(node, id, 'OutC Mode', 0) #disable
            res = set_parameter_byindexorname(node, id, 'OutC1 Index', -1)
            
        if number_of_escs_per_escnode > 5:
            res = set_parameter_byindexorname(node, id, 'OutC2 Index', esc_indexes[current_index_pos])
            current_index_pos += 1
        else:
            res = set_parameter_byindexorname(node, id, 'OutC2 Index', -1)


#---------------------------------------------------------
# ArduPilot motor maping stuff
#---------------------------------------------------------

cAPVEHICLETPYE_XQUAD = 0

#map the motors to the ArduPilot indices
ap_motor_esc_map = {}
ap_motor_esc_map_keys = []


def setAPVehicleType(vehicle=cAPVEHICLETPYE_XQUAD):
    pass
    

def setAPXQuadMotorEscMap():
    global ap_motor_esc_map
    global ap_motor_esc_map_keys
    ap_motor_esc_map = { 'A': 0, 'B': 3, 'C': 1, 'D': 2 }
    ap_motor_esc_map_keys = ap_motor_esc_map.keys()


def setAPMotorEscMap():
    #only x quad currently
    setAPXQuadMotorEscMap()


def printAPXQuadMotorConfiguration():
    print(' ->        <- ')
    print(' D          A ')
    print('   *      *   ')
    print('     *  *     ')
    print('     *  *     ')
    print('   *      *   ')
    print(' C          B ')
    print(' ->        <- ')

    
def printAPMotorConfiguration():
    #only x quad currently
    printAPXQuadMotorConfiguration()
            
            
#---------------------------------------------------------
# MAIN
#---------------------------------------------------------
if __name__ == '__main__':

    #---------------------------------------------------------
    # user adjustable parameters
    #---------------------------------------------------------

#    slcan_com = 'COM38'
    
#    number_of_escs_per_escnode = 1

#    motor_spin_inpercent = 10
    
    
    #---------------------------------------------------------
    # let's go
    #---------------------------------------------------------
    print('----------------------------------------------------------------')
    print('Semiautomatic interactive setup for UC4H ESC nodes')
    print(version_str,' (c) www.olliw.eu')
    print('----------------------------------------------------------------')
    print('Check of user parameters')
    print('  SLCAN com port:',slcan_com)
    print('  Number of ESCs per node:',number_of_escs_per_escnode)
    print('All OK? (y/n)')
    if not pressYesNo(): sys.exit(0)
        
    print()
    node_monitor, node = createNode(slcan_com);
   
    all_node_ids = sorted(list(node_monitor.get_all_node_id()))
    print( '\nDetected nodes' )
    for id in all_node_ids:
        d = node_monitor.get(id)
        print('  ',d.node_id,':',d.info.name)
    
    esc_node_ids = detect_all_uc4h_escs(node_monitor, node)
    print( '\nUC4H ESC nodes:',esc_node_ids )
    
    '''
    esc_node_indices, esc_index_id = get_uc4h_esc_indicies(node, esc_node_ids)
    print( esc_node_indices )
    print( esc_index_id  )
    '''
    #pressKeyboardToContinue(node)

    #determine the number of ESCs in the system, from the number of detected ESC nodes, and the user specified number of ESCs per node
    number_of_escs = len(esc_node_ids) * number_of_escs_per_escnode
    print('Number of ESCs:', number_of_escs)

    def emptyCommands():
        return [0]*number_of_escs
    
    # and reset all escs, just to be sure
    node.broadcast(uavcan.equipment.esc.RawCommand(cmd = emptyCommands()))
    
    # now set all ESC indices to our default
    esc_startup_order = []
    for i in range(number_of_escs): esc_startup_order.append(i)
    print('Startup index order:',esc_startup_order)
   
    set_uc4h_esc_indicies(node, esc_node_ids, esc_startup_order)
    
    for id in esc_node_ids:
        print('  executeopcode save for node',id)
        res = execute_opcode(node, id, 0)
    
    for id in esc_node_ids:
        print('  restart node',id)
        res = restart_node(node, id)
    
    print()
    waitForAllNodes(node_monitor, node)   
    
    # all ESCs are no indexed from 0...number_of_escs-1
    # however the order is arbitrary
    # so we next try to get the correct order by spining each motor and asking the user for input
    
    def emptyCommands():
        return [0]*number_of_escs
    
    # and reset all escs, just to be sure
    message = uavcan.equipment.esc.RawCommand(cmd = emptyCommands())
    node.broadcast(message)
    
    print()
    print('----------------------------------------------------------------')
    print('The motors will now be ramped up individually')
    print('Please connect power, and wait until ESCs are armed')
    print('----------------------------------------------------------------')
    pressKeyboardToContinue(node)
    
    #map the motors to the ArduPilot indices
    setAPVehicleType(cAPVEHICLETPYE_XQUAD)
    setAPMotorEscMap()

    #go through the user input      
    esc_motor_order = []
    esc_motor_order_set = set() #is only used to test for double entries
    #'''
    current_target_index = 0
    for id in esc_node_ids:
        for i in range(number_of_escs_per_escnode):
            print()
            print( 'Spin motor on node id',id,'and index',current_target_index)
            print( 'Please type in which motor you see spinning (A,B,C,D)')
            print( 'you have 30 secs time before the motor stops')
            print()
            printAPMotorConfiguration()

            commands = emptyCommands()
            commands[current_target_index] = int(81*motor_spin_inpercent) #that's accurate enought #1000
            node.broadcast(uavcan.equipment.esc.RawCommand(cmd = commands))
            
            tmo_time = time.time() + 30.0
            is_spinning = True
            while True:
                if is_spinning and (time.time() > tmo_time):
                    print( 'motor stopped')
                    print( 'please continue making your choice, or hit any key to abort')
                    node.broadcast(uavcan.equipment.esc.RawCommand(cmd = emptyCommands()))
                    is_spinning = False
                    
                motor = getKey(node).upper()
                if motor in ap_motor_esc_map_keys:
                    if motor in esc_motor_order_set:
                            print(motor,'has been already selected for another motor. Please repeat')
                    else:
                        print('->',motor)
                        esc_motor_order_set.add(motor)
                        esc_motor_order.append(motor)
                        break
                else:
                    if not is_spinning: 
                        print('ABORT')
                        break

            node.broadcast(uavcan.equipment.esc.RawCommand(cmd = emptyCommands()))

            pressKeyboardToContinue(node)
            current_target_index += 1
    #'''
    #esc_motor_order = ['A','C','D','B']            
          
    print()
    print('Determined motor order:',esc_motor_order)
    
    esc_final_order = []
    for i in range(len(esc_motor_order)):
        for key in ap_motor_esc_map_keys:
            if esc_motor_order[i] == key: esc_final_order.append(ap_motor_esc_map[key])
    print('Corresponding ESC indices:',esc_final_order)

    set_uc4h_esc_indicies(node, esc_node_ids, esc_final_order)

    for id in esc_node_ids:
        print('  executeopcode save for node',id)
        res = execute_opcode(node, id, 0)
    
    for id in esc_node_ids:
        print('  restart node',id)
        res = restart_node(node, id)
    
    print()
    waitForAllNodes(node_monitor, node)   
    
    print()
    print('----------------------------------------------------------------')
    print('Double-check the index assigmenets')
    print('press a,b,c,d to spin the respective motor')
    print('press q to abort')
    print('----------------------------------------------------------------')

    while True:
        print()
        print('enter key>')
        c = getKey(node).upper()
        if c in ap_motor_esc_map_keys:
            current_target_index = ap_motor_esc_map[c]
            
            print()
            print( 'Spin motor',c,'with index',current_target_index)
            print()
            printAPMotorConfiguration()

            commands = emptyCommands()
            commands[current_target_index] = int(81*motor_spin_inpercent) #that's accurate enought #1000
            node.broadcast(uavcan.equipment.esc.RawCommand(cmd = commands))
        else:
            commands = emptyCommands()
            node.broadcast(uavcan.equipment.esc.RawCommand(cmd = commands))
            if c == 'Q': break

    print()
    print('----------------------------------------------------------------')
    print('DONE')
    print('Have fun :)')
    print('----------------------------------------------------------------')
        
    
    
    
    
    