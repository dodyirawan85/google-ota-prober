#!/usr/bin/python3

from checkin import checkin_generator_pb2
from google.protobuf import text_format
from utils import functions
import argparse, requests, gzip, shutil, os, yaml

def load_config(config_file):
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)

parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true', help='Print debug information to text file.')
parser.add_argument('-c', '--config', default='config.yml', help='Path to the config file')
args = parser.parse_args()

config = load_config(args.config)

current_build = config['build_tag']
current_incremental = config['incremental']
android_version = config['android_version']
model = config['model']
device = config['device']
oem = config['oem']
product = config['product']

headers = {
    'accept-encoding': 'gzip, deflate',
    'content-encoding': 'gzip',
    'content-type': 'application/x-protobuffer',
    'user-agent': f'Dalvik/2.1.0 (Linux; U; Android {android_version}; {model} Build/{current_build})'
}

checkinproto = checkin_generator_pb2.AndroidCheckinProto()
payload = checkin_generator_pb2.AndroidCheckinRequest()
build = checkin_generator_pb2.AndroidBuildProto()
response = checkin_generator_pb2.AndroidCheckinResponse()

# Add build properties
build.id = f'{oem}/{product}/{device}:{android_version}/{current_build}/{current_incremental}:user/release-keys' # Put the build fingerprint here
build.timestamp = 0
build.device = device

# Checkin proto
checkinproto.build.CopyFrom(build)
checkinproto.lastCheckinMsec = 0
checkinproto.roaming = "WIFI::"
checkinproto.userNumber = 0
checkinproto.deviceType = 2
checkinproto.voiceCapable = False
checkinproto.unknown19 = "WIFI"

# Generate the payload
payload.imei = functions.generateImei()
payload.id = 0
payload.digest = functions.generateDigest()
payload.checkin.CopyFrom(checkinproto)
payload.locale = 'en-US'
payload.macAddr.append(functions.generateMac())
payload.timeZone = 'America/New_York'
payload.version = 3
payload.serialNumber = functions.generateSerial()
payload.macAddrType.append('wifi')
payload.fragment = 0
payload.userSerialNumber = 0
payload.fetchSystemUpdates = 1
payload.unknown30 = 0

with open('test_data.txt', 'wb') as f:
    f.write(payload.SerializeToString())
    f.close()

with open('test_data.txt', 'rb') as f_in:
    with gzip.open('test_data.gz', 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
        f_out.close()
    f_in.close()

post_data = open('test_data.gz', 'rb')
r = requests.post('https://android.googleapis.com/checkin', data=post_data, headers=headers)
post_data.close()
try:
    found = False
    response.ParseFromString(r.content)
    if args.debug:
        with open('debug.txt', 'w') as f:
            f.write(text_format.MessageToString(response))
            f.close()
    for entry in response.setting:
        if b'https://android.googleapis.com' in entry.value:
            print("OTA URL obtained: " + entry.value.decode())
            found = True
            break
    if found:
        for entry in response.setting:
            if entry.name.decode() == "update_description":
                print("\nCHANGELOG:\n" + entry.value.decode())
                break
    if not found:
        print("No OTA URL found for your build. Either Google does not recognize your build fingerprint, or there are no new updates for your device.")
except: # This should not happen.
    print("Unable to obtain OTA URL.")
