vrnetlab / HP VSR1000
======================
This is the vrnetlab docker image for HP VSR1000.


Need to figure out a way to send these commands through QEMU:

<HP>system-view
[HP]user-interface aux 0
[HP-line-aux0]authentication-mode none
[HP-line-aux0]user-role network-admin
[HP-line-aux0]quit

Prereq to be able to access the box after startup.
