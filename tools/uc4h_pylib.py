#!/usr/bin/env python3
'''
OlliW 28.Feb.2018
'''

#based on the example here: http://uavcan.org/Implementations/Pyuavcan/Examples/ESC_throttle_control/
#see https://groups.google.com/forum/#!topic/uavcan/cz7UBGZTdF8 for how to get things working on Win
# thx, Pavel !

import uavcan, time
import msvcrt, sys


#---------------------------------------------------------
# convenience functions
#---------------------------------------------------------

def printX(s):
    print(s, end='', flush=True)


def delay_sec(node,tme): 
    node.spin(tme)

    
#---------------------------------------------------------
# keyboard convenience functions
#---------------------------------------------------------
    
def clearKeys():
    while msvcrt.kbhit(): msvcrt.getch() #clear all chars in the buffer
    

def pressKeyboardToContinue(node=None,force=True):
    printX('\npress any key to continue... ')
    if force: clearKeys() 
    while True:
        try:
            if node: node.spin(0.1)
            if msvcrt.kbhit():
                msvcrt.getch()
                print()
                break
        except KeyboardInterrupt:
            sys.exit(0)

            
def pressYesNo(s,node=None,force=True):
    if force: clearKeys()
    printX(s+' (y/n)? ')
    while True:
        try:
            if node: node.spin(0.1)
            if msvcrt.kbhit():
                c = msvcrt.getch()
                if (c == b'y') or (c == b'Y'): 
                    print('y')
                    return True
                print('n')    
                return False
                #break
        except KeyboardInterrupt:
            sys.exit(0)
    print('n')        
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

    
def getKeyNonblocking(node=None,force=False):
    if force: clearKeys() 
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
    
def getParameterByIndexOrNname(node,target_node_id,indnam,return_yaml=False,force=True):

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
        

def getParameters(node,target_node_id):
    for i in range(100): #don't accept more than 100 parameters
        res,param = get_parameter_byindexorname(node,target_node_id,i)
        if not res: return
        print(param['name'], ':', param['value'])


def setParameterByIndexOrName(node,target_node_id,indnam,intfloatvalue):
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


def executeOpcode(node,target_node_id,intopcode=0): #0: OPCODE_SAVE  1: OPCODE_ERASE
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
    
    
def restartNode(node,target_node_id):
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

def waitForAllNodesDynamicId(dynamic_node_id_allocator,node):
    
    detected_number_of_nodes = 0
    detect_cnt = 3 #look 3 seconds for changes in the number of nodes
    printX('Waiting for all nodes to become online .')
    while detect_cnt or not detected_number_of_nodes:
        printX('.')
        node.spin(timeout=1)
        #n = len(node_monitor.get_all_node_id())
        n = len(dynamic_node_id_allocator.get_allocation_table())
        
        node.spin(timeout=1)
        if n > 0:
            detect_cnt -= 1
            if n > detected_number_of_nodes:
                detected_number_of_nodes = n
                detect_cnt = 3
    print('ok')
    
        
def createNodeDynamicId(com):
    node = uavcan.make_node(com, node_id=126, bitrate=1000000, baudrate=1000000)

    node_monitor = uavcan.app.node_monitor.NodeMonitor(node)
    dynamic_node_id_allocator = uavcan.app.dynamic_node_id.CentralizedServer(node, node_monitor)
    
    waitForAllNodesDynamicId(dynamic_node_id_allocator,node)
        
    return node_monitor, node, dynamic_node_id_allocator

    
def waitForAllNodes(node_monitor,node):
    
    detected_number_of_nodes = 0
    detect_cnt = 3 #look 3 seconds for changes in the number of nodes
    printX('Waiting for all nodes to become online .')
    while detect_cnt or not detected_number_of_nodes:
        printX('.')
        node.spin(timeout=1)
        n = len(node_monitor.get_all_node_id())
        if n > 0:
            detect_cnt -= 1
            if n > detected_number_of_nodes:
                detected_number_of_nodes = n
                detect_cnt = 3
    print('ok')
    
        
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
def detectEscNodesByMessage(node):
    esc_nodes = set()
    handle = node.add_handler(uavcan.equipment.esc.Status, lambda event: esc_nodes.add(event.transfer.source_node_id))
    try:
        node.spin(timeout=3)            # Collecting ESC status messages, thus determining which nodes are ESC
    finally:
        handle.remove()

    return esc_nodes

    
def detectUc4hNodesByName(node_monitor):
    esc_nodes = set()
    powerbrick_nodes = set()
    all_node_ids = sorted(list(node_monitor.get_all_node_id()))
    for id in all_node_ids:
        n = str(node_monitor.get(id).info.name)
        print(n)
        if '-esc-' in n: esc_nodes.add(id)
        if '-powerbrick-' in n: powerbrick_nodes.add(id)
        
    return esc_nodes, powerbrick_nodes
    
        
def detectUc4hNodesAllEscs(node_monitor,node):
    esc_node_ids_set = set()
    all_node_ids = sorted(list(node_monitor.get_all_node_id()))
    for id in all_node_ids:
        n = str(node_monitor.get(id).info.name)
        if 'uc4h-esc' in n: esc_node_ids_set.add(id)
    return sorted(list(esc_node_ids_set))

    

    