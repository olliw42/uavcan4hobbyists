#!/usr/bin/env python3
'''
OlliW 25.Mar.2018
Script for half-automated setup of UC4H ESC nodes
'''
import uavcan, time, math
import msvcrt, sys

from uc4h_pylib import *
from uc4h_aplib import *


version_str = '31.Mar.2018 v003'


#---------------------------------------------------------
# user adjustable parameters
#---------------------------------------------------------

slcan_com = 'COM38'
    
vehicle_type = cAPVEHICLETPYE_XQUAD

motor_pole_pairs = 14

node_id_default_base = 60

motor_spin_inpercent =  3 # 10


    
#---------------------------------------------------------
# UC4H ESC specific functions
#---------------------------------------------------------

def set_uc4h_esc_indicies(node, esc_node_ids, esc_indexes, esc_directions):
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
        print('  set esc indices and directions for node',id,'to',s)

        #this could be done more elegantly, but let's do it stupidly
        if number_of_escs_per_escnode > 0:
            res = setParameterByIndexOrName(node, id, 'OutA Mode', 3) #sets DSHOT
            res = setParameterByIndexOrName(node, id, 'OutA1 Index', esc_indexes[current_index_pos])
            res = setParameterByIndexOrName(node, id, 'OutA1 Direction', esc_directions[current_index_pos])
            current_index_pos += 1
        else:
            res = setParameterByIndexOrName(node, id, 'OutA Mode', 0) #disable
            res = setParameterByIndexOrName(node, id, 'OutA1 Index', -1)
            res = setParameterByIndexOrName(node, id, 'OutA1 Direction', 0)
            
        if number_of_escs_per_escnode > 1:
            res = setParameterByIndexOrName(node, id, 'OutA2 Index', esc_indexes[current_index_pos])
            res = setParameterByIndexOrName(node, id, 'OutA2 Direction', esc_directions[current_index_pos])
            current_index_pos += 1
        else:
            res = setParameterByIndexOrName(node, id, 'OutA2 Index', -1)
            res = setParameterByIndexOrName(node, id, 'OutA2 Direction', 0)
         
        if number_of_escs_per_escnode > 2:
            res = setParameterByIndexOrName(node, id, 'OutB Mode', 3) #sets DSHOT
            res = setParameterByIndexOrName(node, id, 'OutB1 Index', esc_indexes[current_index_pos])
            res = setParameterByIndexOrName(node, id, 'OutB1 Direction', esc_directions[current_index_pos])
            current_index_pos += 1
        else:
            res = setParameterByIndexOrName(node, id, 'OutB Mode', 0) #disable
            res = setParameterByIndexOrName(node, id, 'OutB1 Index', -1)
            res = setParameterByIndexOrName(node, id, 'OutB1 Direction', 0)
            
        if number_of_escs_per_escnode > 3:
            res = setParameterByIndexOrName(node, id, 'OutB2 Index', esc_indexes[current_index_pos])
            res = setParameterByIndexOrName(node, id, 'OutB2 Direction', esc_directions[current_index_pos])
            current_index_pos += 1
        else:
            res = setParameterByIndexOrName(node, id, 'OutB2 Index', -1)
            res = setParameterByIndexOrName(node, id, 'OutB2 Direction', 0)

        if number_of_escs_per_escnode > 4:
            res = setParameterByIndexOrName(node, id, 'OutC Mode', 3) #sets DSHOT
            res = setParameterByIndexOrName(node, id, 'OutC1 Index', esc_indexes[current_index_pos])
            res = setParameterByIndexOrName(node, id, 'OutC1 Direction', esc_directions[current_index_pos])
            current_index_pos += 1
        else:
            res = setParameterByIndexOrName(node, id, 'OutC Mode', 0) #disable
            res = setParameterByIndexOrName(node, id, 'OutC1 Index', -1)
            res = setParameterByIndexOrName(node, id, 'OutC1 Direction', 0)
            
        if number_of_escs_per_escnode > 5:
            res = setParameterByIndexOrName(node, id, 'OutC2 Index', esc_indexes[current_index_pos])
            res = setParameterByIndexOrName(node, id, 'OutC2 Direction', esc_directions[current_index_pos])
            current_index_pos += 1
        else:
            res = setParameterByIndexOrName(node, id, 'OutC2 Index', -1)
            res = setParameterByIndexOrName(node, id, 'OutC2 Direction', 0)

            
#---------------------------------------------------------
# helpers
#---------------------------------------------------------

def saveRestartWait(node_monitor, node, esc_node_ids):
    for id in esc_node_ids:
        print('  executeopcode save for node',id)
        res = executeOpcode(node, id, 0)
    
    for id in esc_node_ids:
        print('  restart node',id)
        res = restartNode(node, id)
    
    print()
    #waitForAllNodesDynamicId(dynamic_node_id_allocator, node)   
    waitForAllNodes(node_monitor, node) #seems to work, but only if createNodeDynamicId() was used before !!


def doAbort(s=''):
    print('----------------------------------------------------------------')
    if s != '':
        print(s)
    print('ABBORTED')
    print('----------------------------------------------------------------')
    sys.exit(0)
   

#---------------------------------------------------------
# MAIN
#---------------------------------------------------------
if __name__ == '__main__':

    apInit(vehicle_type)
    ap_motor_esc_map = apMotorEscMap()
    ap_motor_esc_map_keys = apMotorEscMap().keys()

    #---------------------------------------------------------
    # let's go
    #---------------------------------------------------------
    print('================================================================')
    print('Semiautomatic interactive setup for UC4H ESC nodes')
    print(version_str,' (c) www.olliw.eu')
    print('================================================================')
    print('Check of user parameters')
    print('  SLCAN com port:',slcan_com)
    print('  ArduPilot vehicle type:',apVehicleTypeStr())
    print('  motor pole pairs:',motor_pole_pairs)
#XX    if not pressYesNo('All OK'): sys.exit(0)

    print()
    print('Make your choice:')
    print('  a) all configuration steps' )
    print('  b) esc default configuration')
    print('  c) determine indices and directions (needs a)')
    print('  d) test motor assignment')
    print('  q) quit')
    print('  any other key does all configuration steps')
    printX('> ')
    menuchoice = getKey().lower()
    if menuchoice == 'q':
        print('quit')
        sys.exit(0)
    if menuchoice not in ('b','c','d'):  menuchoice = 'all'
    print(menuchoice)        
        
    print()
    #node_monitor, node = createNode(slcan_com); #seems to work also for dynamic ids! But a waitForAllNodes() later does hang up
    node_monitor, node, dynamic_node_id_allocator = createNodeDynamicId(slcan_com);

    print( '\nDetected nodes' )
    for id in sorted(list(node_monitor.get_all_node_id())):
        d = node_monitor.get(id)
        print('  ',d.node_id,':',d.info.name)

    #---------------------------------------------------------
    # determine number of ESCs, and number of ESCs per node
    #---------------------------------------------------------

    #determine the number of UC4H ESCs 
    esc_node_ids = detectUc4hNodesAllEscs(node_monitor, node)
    print( '\nUC4H ESC nodes:',esc_node_ids )
    
    #determine the number of ESCs per node
    # from the number of detected ESC nodes, and the user specified number of ESCs
    # number_of_escs = len(esc_node_ids) * number_of_escs_per_escnode
    number_of_escs = apMotorNumber()
    number_of_escs_per_escnode = number_of_escs / len(esc_node_ids)
    print('  number of ESCs:', number_of_escs)
    print('  number of ESCs per node:',number_of_escs_per_escnode)
    
    if not number_of_escs_per_escnode.is_integer():
        doAbort('Number of ESCs is not a multiple of the number of Nodes')
        
    number_of_escs_per_escnode = int(number_of_escs_per_escnode)
    
    def zeroEscCommand():
        return [0]*number_of_escs
    
    #disarm/set to zero all escs, just to be sure
    node.broadcast(uavcan.equipment.esc.RawCommand(cmd = zeroEscCommand()))
    
    #---------------------------------------------------------
    # set UC4H ESC parameter to defaults, inclusive node ids
    #---------------------------------------------------------
    if menuchoice in ('b','all'):
    
        #set all ESC indices to default, set output mode to DSHOT, directions to 0
        esc_startup_order = []
        esc_startup_direction = []
        for i in range(number_of_escs): 
            esc_startup_order.append(i)
            esc_startup_direction.append(0)
        print('\nStartup index order:',esc_startup_order)
   
        set_uc4h_esc_indicies(node, esc_node_ids, esc_startup_order, esc_startup_direction)
        
        for id in esc_node_ids:
            print('  set motor poles for node',id,'to',motor_pole_pairs)
            res = setParameterByIndexOrName(node, id, 'Motor Pole Pairs', motor_pole_pairs)
        
        current_node_id = node_id_default_base
        for id in esc_node_ids:
            print('  set node id for node',id,'to',current_node_id)
            res = setParameterByIndexOrName(node, id, 'NodeId', current_node_id)
            current_node_id += 1
    
        saveRestartWait(node_monitor, node, esc_node_ids)
        node.broadcast(uavcan.equipment.esc.RawCommand(cmd = zeroEscCommand()))

        esc_node_ids = detectUc4hNodesAllEscs(node_monitor, node)
        print( '\nUC4H ESC nodes:',esc_node_ids )
        
        #set all ESC directions to normal
        # we also need to ensure that this is stored not only into the node but also into the ESC
        # thus: i) the node needs to have be restarted/repowered (to activate DSHOT)
        #       ii) the ESC needs to be repowered (so it works with DSHOT)
        #       iii) executeopcode save needs to be invoked (so to that the directiosn are actually written to the ESC)

        # REPOWER ESCS
        print()
        print('----------------------------------------------------------------')
        print('ATTENTION: All ESCs need to be REPOWERED now !!!')
        print('>>>>>  REMOVE ALL PROPS  <<<<<')
        print('Please continue when done')
        printX('----------------------------------------------------------------')
        pressKeyboardToContinue(node)

        print('\nSet ESC directions')
        for id in esc_node_ids:
            print('  executeopcode save for node',id) #this writes the DSHOT_SPIN_DIRECTION1 commdns to the ESCs
            res = executeOpcode(node, id, 0)
    
        delay_sec(node,2) 
        node.broadcast(uavcan.equipment.esc.RawCommand(cmd = zeroEscCommand()))
    
    #---------------------------------------------------------
    # spin motors to determine correct sequence of indices, and directions
    #---------------------------------------------------------
    if menuchoice in ('c','all'):
    
        # all ESCs are now indexed from 0...number_of_escs-1
        # however the order is arbitrary
        # so we next try to get the correct order by spining each motor and asking the user for input
        # also, all ESCs have now spindirection1
        # so we next also try to get the correct directions
    
        print()
        print('----------------------------------------------------------------')
        print('The motors will now be ramped up individually')
        print('>>>>>  REMOVE ALL PROPS  <<<<<')
        print('If not done already, please remove props, connect power,')
        print('and wait until ESCs are armed')
        printX('----------------------------------------------------------------')
        pressKeyboardToContinue(node)
    
        print()
        print('----------------------------------------------------------------')
        print('You for sure have seen this, right?')
        print('>>>>>                    <<<<<')
        print('>>>>>  REMOVE ALL PROPS  <<<<<')
        print('>>>>>                    <<<<<')
        print('If not yet done, please do now')
        print('----------------------------------------------------------------')
        if not pressYesNo('Props removed'): sys.exit(0)
    
        #go through the user input      
        esc_motor_order = []
        esc_motor_order_set = set() #is only used to test for double entries
        esc_motor_direction = []
    
        current_target_index = 0
        for id in esc_node_ids:
            for channel in range(number_of_escs_per_escnode):
                print()
                print( 'Spin motor with index',current_target_index)
                print( 'Please type in which motor you see spinning (A,B,C,D,...)')
                print( 'You will also be asked if the spin direction is correct or not, so watch it')
                print( 'You have 30 secs time before the motor stops')
                print( 'press q to abort')
                print()
                printAPMotorConfiguration()
                printX('\nmotor> ')

                commands = zeroEscCommand()
                commands[current_target_index] = int(81*motor_spin_inpercent) #that's accurate enought #1000
                node.broadcast(uavcan.equipment.esc.RawCommand(cmd = commands))
            
                tmo_time = time.time() + 15.0 #XX30.0
                is_spinning = True
                is_aborted = False
                while not is_aborted:
                    if is_spinning and (time.time() > tmo_time):
                        print( '\nmotor stopped')
                        print( 'please continue making your choice, or hit any key to abort')
                        printX('motor> ')
                        node.broadcast(uavcan.equipment.esc.RawCommand(cmd = zeroEscCommand()))
                        is_spinning = False
                    
                    motor = getKeyNonblocking(node).upper()
                    if motor in ap_motor_esc_map_keys:
                        if motor in esc_motor_order_set:
                            print(motor,'has been already selected for another motor. Please repeat')
                            printX('motor> ')
                        else:
                            print(motor)
                            esc_motor_order_set.add(motor)
                            esc_motor_order.append(motor)
                            printX('direction OK (y/n)> ')
                            while not is_aborted:
                                c = getKey(node).upper()
                                if c == 'N':
                                    print('n')
                                    esc_motor_direction.append(1)
                                    break
                                elif c == 'Y':
                                    print('y')
                                    esc_motor_direction.append(0)
                                    break
                                elif c == 'Q':
                                    print()
                                    is_aborted = True
                                    break
                            break
                    elif motor == 'Q':
                        print()
                        is_aborted = True
                        break
                
                node.broadcast(uavcan.equipment.esc.RawCommand(cmd = zeroEscCommand()))
            
                if is_aborted: doAbort()
            
                current_target_index += 1
                if current_target_index != number_of_escs:    
                    printX('\npress any key to continue with next motor... ')
                    c = getKey(node).upper()
                    print()
    
        #esc_motor_order = ['A','C','D','B']            
          
        print()
        print('Determined motor order:',esc_motor_order)
        print('Determined motor directions:',esc_motor_direction)
    
        esc_final_order = []
        for i in range(len(esc_motor_order)):
            for key in ap_motor_esc_map_keys:
                if esc_motor_order[i] == key: esc_final_order.append(ap_motor_esc_map[key])
        print('Corresponding ESC indices:',esc_final_order)

        set_uc4h_esc_indicies(node, esc_node_ids, esc_final_order, esc_motor_direction)

        saveRestartWait(node_monitor, node, esc_node_ids)
        node.broadcast(uavcan.equipment.esc.RawCommand(cmd = zeroEscCommand()))
        delay_sec(node,2)
    
    #---------------------------------------------------------
    # test motors
    #---------------------------------------------------------
    if menuchoice in ('d','all'):
    
        print()
        print('----------------------------------------------------------------')
        print('Double-check the index assigmenets')
        print('press a,b,c,d,... to spin the respective motor')
        print('press q to abort')
        print('----------------------------------------------------------------')

        print()
        printAPMotorConfiguration()
        print()
        
        while True:
            printX('enter key> ')
            c = getKey(node).upper()
            if c in ap_motor_esc_map_keys:
                current_target_index = ap_motor_esc_map[c]
                print( 'Spin motor',c,'with index',current_target_index)
                commands = zeroEscCommand()
                commands[current_target_index] = int(81*motor_spin_inpercent) #that's accurate enought #1000
                node.broadcast(uavcan.equipment.esc.RawCommand(cmd = commands))
            else:
                print()
                node.broadcast(uavcan.equipment.esc.RawCommand(cmd = zeroEscCommand()))
                if c == 'Q': break
            
    #---------------------------------------------------------
    # DONE
    #---------------------------------------------------------
    
    print()
    print('----------------------------------------------------------------')
    print('DONE')
    print('Have fun :)')
    print('----------------------------------------------------------------')
    print()
        
    
    
    
    
    