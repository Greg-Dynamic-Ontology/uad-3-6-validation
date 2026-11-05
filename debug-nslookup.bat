nslookup -debug -type=NS dynamicontology.com 1.1.1.1
nslookup -debug -type=A dynamicontology.com dns1.registrar-servers.com
nslookup -debug -type=A dynamicontology.com dns2.registrar-servers.com
nslookup -debug -type=CNAME www.dynamicontology.com dns1.registrar-servers.com
nslookup -debug -type=CNAME www.dynamicontology.com dns2.registrar-servers.com