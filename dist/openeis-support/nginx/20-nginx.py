ALLOWED_HOSTS = []
PROTECTED_MEDIA_METHOD = 'X-Accel-Redirect'

try:
    with open('/etc/openeis/server.conf') as file:
        conf = file.read(10000)
except FileNotFoundError:
    pass
else:
    import re
    match = re.search(r'(?:^|\n|{|;)\s*server_name\s+([^;]*);', conf, re.M | re.S)
    if match:
        ALLOWED_HOSTS.extend(match.group(1).split())
