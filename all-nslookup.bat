nslookup -type=NS dynamicontology.com 1.1.1.1
nslookup -type=A dynamicontology.com dns1.registrar-servers.com
nslookup -type=A dynamicontology.com dns2.registrar-servers.com
nslookup -type=CNAME www.dynamicontology.com dns1.registrar-servers.com
nslookup -type=CNAME www.dynamicontology.com dns2.registrar-servers.com