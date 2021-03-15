from json import load
from json import dumps,dump
from pprint import pprint
import sys
import re
import copy

appname = 'Mqtt'
app_proto = 'raw'
sample_action = None
sample_transaction = None

def apply_topic_substitution(self, payl, params):
    stopic = params.get("topic", None)
    stlen = len(stopic)
    r = cutils.ReplacePattern( b'#{@transactionParameters.topicname}', stopic, cutils.APPLY_URL_ENCODE )
    modif = r.apply_pattern_substitution( payl)

    paylen = len(modif) - 2 #first type byte  + second length byte

    return bytes(modif[0] + [paylen] + modif[2:4]) + (stlen).to_bytes(2, byteorder='big') + bytearray(modif)[ 2: ]

def get_json(input):
    with open(input, 'r')  as f:
        json_data = load(f)
    return json_data

def write_json(newjs, dest):
    newFname = dest
    with open(newFname, 'w') as jsf:
        dump(newjs, jsf, indent=2)

src = sys.argv[1]
dest = sys.argv[2]

j = get_json(  src )

sample_transaction = copy.deepcopy ( j['metadata']["scenario"]['items'][0] )
sample_transaction_action = sample_transaction['items']
sample_action = copy.deepcopy( sample_transaction_action[0] )
sample_transaction['items'] = []
j['metadata']["scenario"]['items'] = [] #remove all transactions
j['metadata']["schema"]['definitions']['transaction.name']['enum'] = []

trans_params_regex = re.compile('transaction\.[\w]*\.parameters')

#tparams = None
transaction_description = None

def delete_transaction_param_details(tnames):
    delete_keys  = []
    for k in j['metadata']["schema"]['definitions']:
        if trans_params_regex.match(k):
            if k not in ('transaction.default.parameters','transaction.fill.parameters'):
                delete_keys.append(k)
    tparams = copy.deepcopy( j['metadata']["schema"]['definitions'][delete_keys[0]] )
    for k in delete_keys:
        if len(tnames) > 0:   
            tname = tnames.pop() 
            print(f"replacing trans name is {tname}")
            j['metadata']["schema"]['definitions']['transaction.'+ tname.lower()+'.parameters']= j['metadata']["schema"]['definitions'].pop(k)
        else:
            del j['metadata']["schema"]['definitions'][k]

    #if there are still transactions remaining
    for tname in tnames:
        print(f"tname is {tname}")
        j['metadata']["schema"]['definitions']['transaction.'+ tname.lower()+'.parameters'] = tparams 
           

def application_transaction_details(tr_names):
    o = j['metadata']["schema"]['definitions']['application.transaction']['allOf'][0]
    #print (o['if']['properties']['transaction']['const'])
    #print (o['then']['properties']['transactionParameters']['$ref'])
    transaction_description = copy.deepcopy(o)
    j['metadata']["schema"]['definitions']['application.transaction']['allOf'] = []
    for tr in tr_names:
        nt = copy.deepcopy(transaction_description)
        nt['if']['properties']['transaction']['const'] = tr
        nt['then']['properties']['transactionParameters']['$ref'] = f"#/definitions/transaction.{tr.lower()}.parameters"
        j['metadata']["schema"]['definitions']['application.transaction']['allOf'].append(nt)
        

def add_transaction(trname, actions):
    j['metadata']["schema"]['definitions']['transaction.name']['enum'].append(trname)
    new_transaction = copy.deepcopy(sample_transaction)
    new_transaction['transaction'] = trname
    new_transaction['application'] = appname
    new_transaction['items'] = []
    new_transaction['description'] = appname + " " + trname
    new_transaction['server'] = ['Mqtt Server']
    sdict = set()
    for act in actions:
        new_action = copy.deepcopy( sample_action)
        new_action['action'] = appname.lower() + ' ' + act['action_name']
        new_action['description'] = appname.lower() + ' ' + act['action_name']
        new_action['payload']['name']  = act['payload_name']
        new_action['mslProperties']['fileid']  = act['payload_name']
        new_action['protocol']  = 'raw'
        new_action['server'] = 'Mqtt Server'
        new_transaction['items'].append(new_action)
    j['metadata']["scenario"]['items'].append( new_transaction )

def add_mqtt_specific_transactions():
    add_transaction( 'Connect' ,  [{'action_name':'connectCommand','payload_name':'mqtt.connectCommand.payload'}, {'action_name':'connectAck','payload_name':'mqtt.connectAck.payload'}] )
    add_transaction( 'Subscribe', [{'action_name':'subscribeRequest','payload_name':'mqtt.subscribeRequest.payload'}, {'action_name':'subscribeResponse','payload_name':'mqtt.subscribeResponse.payload'}] )
    add_transaction( 'Publish', [{'action_name':'publishRequest','payload_name':'mqtt.publishMessage.payload'}] )
    add_transaction( 'Ping' ,     [{'action_name':'pingRequest','payload_name':'mqtt.pingRequest.payload'}, {'action_name':'pingResponse','payload_name':'mqtt.pingResponse.payload'}] )

tr_names = ['Connect', 'Subscribe', 'Publish', 'Ping']
application_transaction_details(tr_names)
add_mqtt_specific_transactions()
delete_transaction_param_details( tr_names)
write_json( j, dest )
