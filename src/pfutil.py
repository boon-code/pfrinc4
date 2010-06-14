import socket
import Queue
import threading
import re
# BAD: on windows this wouldn't be possible
import os
import time
import subprocess

import curl

DEFAULT_SOCKET_TIMEOUT = 0.5
DEFAULT_TIMEOUT = 1.0
DEFAULT_RECV_SIZE = 10
UPDATE_INTERVAL = 0.5
LINK_FINDER_STR = "http://([^\",^\n^/,^\\s,^<,^>]+)([^\",^\\s,^\n,^<,^>]*)"
LINK_FINDER_RE = re.compile(LINK_FINDER_STR)
PACKET_NAME_RE = re.compile(".*/([^/]*)[.]{1}part\\d+[.]{1}rar")
PACKET_NAME_SIMPLE_RE = re.compile(".*/([^/]*)[.]{1}rar")
FILENAME_RE = re.compile(".*/([^/]*)")

def resolve_links(links):
    "Scans data and finds links, converts them to rapidshare-links."
    
    def __sjdecode(link):
        "Extract Rapidshare link from Serienjunkies."
        
        site = curl.simple_download(link, '-L')
        result = LINK_FINDER_RE.search(site)
        if result is None:
            return ''
        else:
            return "".join(result.groups())
    
    def __rsdecode(link):
        "Prepare Rapidshare link for final download."
        
        if link == '':
            return ''
        
        site = curl.simple_download(link, '-L')
        pos = site.find("form action")
        
        if pos != -1:
            site = site[pos:]
        
        item = LINK_FINDER_RE.search(site)
        if item is None:
            return ''
        
        path = os.path.split(item.group(2))
        link_end = os.path.join(path[0], 'dl', path[1])
        link = "".join(("http://", item.group(1), link_end))
        return link
    
    resolved_links = []
        
    for link in links:
        if link.startswith("http://download.serienjunkies.org"):
            link = __sjdecode(link)
            link = __rsdecode(link)
            if link != '':
                resolved_links.append(link)
                
        elif link.startswith("http://rapidshare.com"):
            link = __rsdecode(link)
            if link != '':
                resolved_links.append(link)
        
    return resolved_links

def shutdown():
    args = ['smbstatus', '--locks']
    subp = subprocess.Popen(args, stdout=subprocess.PIPE)
    result = subp.communicate()[0]
    
    if result.find("Locked files") < 0:
        args = ['gnome-power-cmd.sh', 'shutdown']
        subp = subprocess.Popen(args, stdout=subprocess.PIPE)
        result = subp.communicate()[0]
        return "init shutdown: " + result
    else:
        return ("failed because of locked files\n%s\n" % result)

def just_shutdown():
    
    #args = ['gnome-power-cmd.sh', 'shutdown']
    args = ['dbus-send', '--print-reply', '--system',
    '--dest=org.freedesktop.Hal', '/org/freedesktop/Hal/devices/computer',
    'org.freedesktop.Hal.Device.SystemPowerManagement.Shutdown']
    
    subp = subprocess.Popen(args, stderr=subprocess.PIPE)
    result = subp.communicate()[1]
    return "init shutdown: " + result
