vrnetlab RPKI RTR speaker
====================
This is vr-gortr, the vrnetlab RPKI RTR speaker. 

It uses the vrnetlab xcon program to connect to a virtual router port. See
vr-xcon for more information on how that works under the hood. This works
very similarly to vr-bgp.

Included is a sample roas.json file.

### `roas.json`
```javascript
{
    "roas": [
        { "asn": "AS1", "prefix": "1.0.0.0/23", "maxLength": 23, "ta": "arin" },
        { "asn": "AS2", "prefix": "2.0.0.0/23", "maxLength": 23, "ta": "ripe" }
    ]
}
```

This is a simple python function to insert a new roas.json file into the
container using docker-py.

### `copy_to`
```python
import docker
import os
import tarfile

def copy_to(docker_host, src, dst):
    """ Copy roas file to a container """
    client = docker.DockerClient(base_url='tcp://' + docker_host + ':2375', timeout=60)
    name, dst = dst.split(':')
    container = client.containers.get(name)

    os.chdir(os.path.dirname(src))
    srcname = os.path.basename(src)
    tar = tarfile.open(src + '.tar', mode='w')
    try:
        tar.add(srcname)
    finally:
        tar.close()

    data = open(src + '.tar', 'rb').read()
    container.put_archive(os.path.dirname(dst), data)

copy_to('172.17.0.1', 'roas.json', vr-gortr:/roas.json')
```
