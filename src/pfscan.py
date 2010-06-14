import os
import re
import curl

SP_LINK = re.compile('http://([^\\",^ ]+)')
#prev = "http://([^\",^\n^/,^\\s,^<,^>]+)([^\",^\\s,^\n,^<,^>]*)"
RSDL_LINK_STR = ("http://(?P<srv>[^ ,^.]+)[.]{1}rapidshare[.]{1}com" + 
    "/files/(?P<link>[^ ,^\\\"]+)")
RSDL_BUILD_STR = "http://%(srv)s.rapidshare.com/files/%(link)s"
RSDL_LINK_RE = re.compile(RSDL_LINK_STR)

def _resolve_link(link):
    
    site = curl.simple_download(link, '-L')
    result = RSDL_LINK_RE.search(site)
    if result is None:
        return None
    else:
        group = result.groupdict()
        path = os.path.split(group['link'])
        group['link'] = os.path.join(path[0], 'dl', path[1])
        return RSDL_BUILD_STR % group


def resolve_links(links):
    
    out = []
    
    for link in links:
        result = _resolve_link(link)
        
        if not (result is None):
            out.append(result)
    
    return out


def scanlinks(data):
    
    lsf = SP_LINK.findall(data)
    links = []
        
    for i in lsf:
        if i.startswith("download.serienjunkies.org"):
            links.append('http://%s' % i)
        elif i.startswith("rapidshare.com"):
            links.append('http://%s' % i)
        
    return links
