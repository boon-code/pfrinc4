import re
import curl

SP_LINK = re.compile('http://([^\\",^ ]+)')
#prev = "http://([^\",^\n^/,^\\s,^<,^>]+)([^\",^\\s,^\n,^<,^>]*)"
RSDL_LINK_STR = ("http://(?P<src>[^ ,^.]+)[.]{1}rapidshare[.]{1}com" + 
    "/files/(?P<link>[^ ,^\\\"]+)")
RSDL_BUILD_STR = "http://%(srv)s.rapidshare.com/files/%(link)s"
RSDL_LINK_RE = re.compile(RS_LINK_STR)

def _resolve_link(link):
    
    site = curl.simple_download(link, '-L')
    result = RSDL_LINK_RE.search(site)
    if result is None:
        return None
    else:
        return RSDL_BUILD_STR % result.groupdict()


def resolve_links(links):
    
    out = []
    
    for link in links:
        result = _resolve_link(link)
        
        if not (result is None):
            out.append(result)


def scanlinks(data):
    
    lsf = SP_LINK.findall(data)
    links = []
        
    for i in lsf:
        if i.startswith("download.serienjunkies.org"):
            links.append('http://%s' % i)
        elif i.startswith("rapidshare.com"):
            links.append('http://%s' % i)
        
    return links
