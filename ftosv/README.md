# Dell FTOSv (OS10) / ftosv

This is the vrnetlab docker image for Dell FTOS10 virtual switch.

## Image Prep

Before we can run `make`, we need to do some prep on the image file. The images can be obtained for free from [Dell's website](https://www.dell.com/support/home/en-us/product-support/product/smartfabric-os10-emp-partner/drivers).

On the computer, you'll need qemu-system-x86_64 and qemu-img installed.

### Steps

For the example, we'll be building 10.5.4.0.98 and the S5248F hardware.

1. Unzip `OS10_Virtualization_{VERSION}.zip`.
2. Decide which platform you want to use.
3. Run qemu to build the image

```bash
sudo /usr/bin/qemu-system-x86_64 -name DellEMCOS10S5248F-10.5.4.0.98-3 \
-m 4096M \
-smp cpus=1,sockets=1 \
-enable-kvm \
-machine smm=off \
-boot order=d \
-device ahci,id=ahci0 \
-drive file=OS10-Disk-1.0.0.vmdk,if=none,id=drive0,index=0,media=disk \
-device ide-hd,drive=drive0,bus=ahci0.0,id=drive0 \
-drive file=OS10-Installer-10.5.4.0.98.vmdk,if=virtio,index=1,media=disk,id=drive1 \
-drive file=OS10-platform-S5248F-10.5.4.0.98.vmdk,if=virtio,index=2,media=disk,id=drive2 \
-uuid 55fd94d9-da24-490c-92c4-663498ee209b \
-serial telnet:127.0.0.1:5006,server,nowait \
-monitor tcp:127.0.0.1:43357,server,nowait \
-display none
```

4. Wait for the image to build. You can monitor this by connecting via `telnet localhost 5006`. This process will take a long time (60+ minutes). Sample output:

```bash
❯ telnet localhost 5006                                                                       
Trying 127.0.0.1...                                                                           
Connected to localhost.                                                                       
Escape character is '^]'.                                                                     
random: nonblocking pool is initialized                                                       
Installation finished. No error reported.                                                     
Info: Using eth0 MAC address: 52:54:00:12:34:56                                               
Info: eth0:  Checking link... up.                                                             
Info: Trying DHCPv4 on interface: eth0                                                        
udhcpc: started, v1.25.1                                                                      
udhcpc: sending discover                                                            
udhcpc: sending select for 10.0.2.15                                                          
udhcpc: lease of 10.0.2.15 obtained, lease time 86400                                         
ONIE: Using DHCPv4 addr: eth0: 10.0.2.15 / 255.255.255.0                                      
Starting: dropbear ssh daemon... done.                                                        
Starting: telnetd... done.                                                                    
discover: installer mode detected.  Running installer.                                        
Starting: discover... done.                                                                   
                                                                                              
Please press Enter to activate this console. Info: eth0:  Checking link... up.                
Info: Trying DHCPv4 on interface: eth0                                                        
ONIE: Using DHCPv4 addr: eth0: 10.0.2.15 / 255.255.255.0                                      
ONIE: Starting ONIE Service Discovery                                                         
Info: Attempting file://dev/vdb1/onie-installer-x86_64-kvm_x86_64-r0 ...                      
Info: Attempting file://dev/vdb1/onie-installer-x86_64-kvm_x86_64 ...                         
Info: Attempting file://dev/vdb1/onie-installer-kvm_x86_64 ...                                
Info: Attempting file://dev/vdb1/onie-installer-x86_64-qemu ...                               
Info: Attempting file://dev/vdb1/onie-installer-x86_64 ...                                    
Info: Attempting file://dev/vdb1/onie-installer ...                                           
Info: Attempting file://dev/vda1/onie-installer-x86_64-kvm_x86_64-r0 ...                      
Info: Attempting file://dev/vda1/onie-installer-x86_64-kvm_x86_64 ...                         
Info: Attempting file://dev/vda1/onie-installer-kvm_x86_64 ...                                
Info: Attempting file://dev/vda1/onie-installer-x86_64-qemu ...                               
Info: Attempting file://dev/vda1/onie-installer-x86_64 ...                                    
Info: Attempting file://dev/vda1/onie-installer ...   
ONIE: Executing installer: file://dev/vda1/onie-installer                           
Initializing installer ... OK                                                                 
Verifying image checksum ... OK                                                               
OS10 Installer: machine: kvm_x86_64/s5248f                                                    
/tmp/os10vm/os10.bin: line 153: onie-syseeprom: not found                                     
Creating partition sda3 ... OK                                                                
Creating partition sda4 ... OK                                                                
Creating physical volume ... OK                                                               
Creating volume group ... OK                                                                  
Creating logical volume LICENSE ... OK                                                        
Creating logical volume SYSROOT ... OK                                                        
Creating ext4 filesystem on LICENSE ... OK                                                    
Creating ext4 filesystem on SYSROOT ... OK                                                    
Extracting OS10 ... OK                                                                        
Installing OS10 on primary volume ... OK                                                      
Setting up shared data ... OK                                                                 
Synchronizing standby image ... OK                                                            
INFO: task umount:18202 blocked for more than 120 seconds.                                    
      Not tainted 4.1.38-onie+ #1                                                             
"echo 0 > /proc/sys/kernel/hung_task_timeout_secs" disables this message.                     
 ffff8801001efc28 ffff8801001efc08 ffff8800ba6dca60 0000000000000000                          
 ffff8801001f0000 ffff8801001efd78 7fffffffffffffff 0000000000000002                          
 ffff8800ba6d8000 ffff8801001efc48 ffffffff815d0794 ffff8801001efd18                          
Call Trace:                                                                                   
 [<ffffffff815d0794>] schedule+0x6f/0x7e  
 [<ffffffff815d27ee>] schedule_timeout+0x26/0x151                                   
 [<ffffffff8104c19b>] ? __queue_work+0x1ec/0x206                                              
 [<ffffffff815d1045>] wait_for_common+0x143/0x1cb                                             
 [<ffffffff81058312>] ? wake_up_process+0x34/0x34                                             
 [<ffffffff815d10e5>] wait_for_completion+0x18/0x1a                                           
 [<ffffffff810ed920>] writeback_inodes_sb_nr+0x8d/0x96                                        
 [<ffffffff810ed94b>] writeback_inodes_sb+0x22/0x29                                           
 [<ffffffff810f1842>] sync_filesystem+0x36/0x90                                               
 [<ffffffff810d01c1>] generic_shutdown_super+0x2c/0xea                                        
 [<ffffffff810d04b5>] kill_block_super+0x22/0x62                                              
 [<ffffffff810d0754>] deactivate_locked_super+0x36/0x63                                       
 [<ffffffff810d0aeb>] deactivate_super+0x3a/0x3e                                              
 [<ffffffff810e69a7>] cleanup_mnt+0x54/0x73                                                   
 [<ffffffff810e69fc>] __cleanup_mnt+0xd/0xf                                                   
 [<ffffffff8104ffce>] task_work_run+0x93/0xad                                                 
 [<ffffffff8100286d>] do_notify_resume+0x40/0x44                                              
 [<ffffffff815d38bc>] int_signal+0x12/0x17                                                    
INFO: task umount:18202 blocked for more than 120 seconds.                                    
      Not tainted 4.1.38-onie+ #1                                                             
"echo 0 > /proc/sys/kernel/hung_task_timeout_secs" disables this message.                     
 ffff8801001efc28 ffff8801001efc08 ffff8800ba6dca60 0000000000000000                          
 ffff8801001f0000 ffff8801001efd78 7fffffffffffffff 0000000000000002                          
 ffff8800ba6d8000 ffff8801001efc48 ffffffff815d0794 ffff8801001efd18                          
Call Trace:                                                                                   
 [<ffffffff815d0794>] schedule+0x6f/0x7e    
 [<ffffffff815d27ee>] schedule_timeout+0x26/0x151                                   
 [<ffffffff8104c19b>] ? __queue_work+0x1ec/0x206                                              
 [<ffffffff815d1045>] wait_for_common+0x143/0x1cb                                             
 [<ffffffff81058312>] ? wake_up_process+0x34/0x34                                             
 [<ffffffff815d10e5>] wait_for_completion+0x18/0x1a                                           
 [<ffffffff810ed920>] writeback_inodes_sb_nr+0x8d/0x96                                        
 [<ffffffff810ed94b>] writeback_inodes_sb+0x22/0x29                                           
 [<ffffffff810f1842>] sync_filesystem+0x36/0x90                                               
 [<ffffffff810d01c1>] generic_shutdown_super+0x2c/0xea                                        
 [<ffffffff810d04b5>] kill_block_super+0x22/0x62                                              
 [<ffffffff810d0754>] deactivate_locked_super+0x36/0x63                                       
 [<ffffffff810d0aeb>] deactivate_super+0x3a/0x3e                                              
 [<ffffffff810e69a7>] cleanup_mnt+0x54/0x73                                                   
 [<ffffffff810e69fc>] __cleanup_mnt+0xd/0xf                                                   
 [<ffffffff8104ffce>] task_work_run+0x93/0xad                                                 
 [<ffffffff8100286d>] do_notify_resume+0x40/0x44                                              
 [<ffffffff815d38bc>] int_signal+0x12/0x17                                                    
OS10 installation is complete.                                                                
Creating ext4 filesystem on sda3 ... OK                                                       
Installing GRUB ... OK                                                                        
Saving system information ... OK                                                              
Saving ONIE support information ... OK                                                        
ONIE: NOS install successful: file://dev/vda1/onie-installer                                  
ONIE: Rebooting...                                                                            
discover: installer mode detected. 
 Stopping: discover...start-stop-daemon: warning: killing process 1766: No such process
 done.                                                                                        
Stopping: dropbear ssh daemon... done.                                                        
Stopping: telnetd... done.                                                                    
Stopping: syslogd... done.                                                                    
Info: Unmounting kernel filesystems                                                           
umount: can't unmount /: Invalid argument                                                     
The system is going down NOW!                                                                 
Sent SIGTERM to all processes                                                                 
Sent SIGKILL to all processes                                                                 
Requesting system reboot                                                                      
sd 0:0:0:0: [sda] Synchronizing SCSI cache                                                    
reboot: Restarting system                                                                     
reboot: machine restart                                                                       
                                                                                              
                          GNU GRUB  version 2.02~beta3                                        
                                                                                              
 +----------------------------------------------------------------------------+               
 |*OS10-A                                                                     |               
 | OS10-B                                                                     |

 | ONIE                                                                       |
 |                                                                            |               
 |                                                                            |               
 |                                                                            |               
 |                                                                            |               
 |                                                                            |               
 |                                                                            |               
 |                                                                            |               
 |                                                                            |               
 |                                                                            |               
 +----------------------------------------------------------------------------+               
                                                                                              
      Use the ^ and v keys to select which entry is highlighted.                              
      Press enter to boot the selected OS, `e' to edit the commands                           
      before booting or `c' for a command-line.                                               
   The highlighted entry will be executed automatically in 0s.                                
  Booting `OS10-A'                                                                            
                                                                                              
Loading OS10 ...                                                                              
[    0.833753] kvm: no hardware support                                                       
[    1.489176] intel_rapl: driver does not support CPU family 15 model 107

Debian GNU/Linux 10 OS10 ttyS0                                                                

Dell EMC Networking Operating System (OS10)                                                   

OS10 login: admin                                                                             
Password:      
```

5. After the login (username: *admin*, password: *admin*), once the system is ready and the prompt appears, you need to **stop ztd** with the command `ztd cancel`. Then, `write memory` and `reload`.
6. Once the reload is completed, you can shutdown the qemu-system host as the image has been built. With 10.5.2.4, it creates an image of approximately 7G.
7. Next is to convert from vmdk to qcow2.

```bash
qemu-img convert -f vmdk -O qcow2 OS10-Disk-1.0.0.vmdk dellftos.{VERSION}.qcow2
```

Once this is complete, you'll be left with a qcow2 image that can then be built with the make command. To help validate output, here are the sizes of the 2 files.


```bash
❯ ls -l
-rw-r--r-- 1 user user 6630014976 Aug 14 17:57 dellftos.10.5.4.0.98.qcow2
-rw-r--r-- 1 user user 7471693824 Aug 14 01:07 OS10-Disk-1.0.0.vmdk

```

## Building the docker image

Put the .qcow2 file in this directory and run make docker-image and you should be good to go. The resulting image is 
called `vr-ftosv`. You can tag it with something else if you want, like `my-repo.example.com/vr-ftosv` and then push it to 
your repo. The tag is the same as the version of the FTOS image, so if you have `dellftos.10.5.2.4.qcow2` your final docker 
image will be called `vr-ftosv:10.5.2.4`

NOTE:

* Dell officially does not provide .qcow2 disk images. Check Dell OS10 virtualization documentation on how to prepare disk image from officially available virtualization package. One can use either GNS3 or EVE-NG to prepare .qcow2 disk.
* Number of interfaces are dependent on FTOS platform used in .qcow2 disk. By default, number of interfaces set under `launch.py` is `56` based on S5248 platform.

## System requirements

* CPU: 4 core
* RAM: 4GB
* Disk: <10GB

