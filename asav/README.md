vrnetlab / Cisco ASAv
===========================
This is the vrnetlab docker image for Cisco ASAv.

Building the docker image
-------------------------
Put the .qcow2 file in this directory and run `make docker-image` and
you should be good to go. The resulting image is called `vr-asav`. You can tag
it with something else if you want, like `my-repo.example.com/vr-asav` and then
push it to your repo. The tag is the same as the version of the ASAv image, so
if you have asav9-18-2.qcow2 your final docker image will be called
vr-asav:9-18-2

Please note that you will always need to specify version when starting your
router as the "latest" tag is not added to any images since it has no meaning
in this context.

It's been tested to boot and respond to SSH with:

 * 9.18.2 (asav9-18-2.qcow2)

Usage
-----
```
docker run -d --privileged --name my-asav-firewall vr-asav
```

Interface mapping
-----------------
Management0/0 is always configured as a management interface.

| vr-asav             | vr-xcon |
| :---:               |  :---:  |
| Management0/0       | 0       |
| GigabitEthernet0/0  | 1       |
| GigabitEthernet0/1  | 2       |
| GigabitEthernet0/2  | 3       |
| GigabitEthernet0/3  | 4       |
| GigabitEthernet0/4  | 5       |
| GigabitEthernet0/5  | 6       |
| GigabitEthernet0/6  | 7       |
| GigabitEthernet0/7  | 8       |

System requirements
-------------------
CPU: 1 core

RAM: 2GB

Disk: <500MB

FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: Has this been extensively tested?
A: Nope. 
