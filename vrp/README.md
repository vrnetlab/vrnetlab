vrnetlab / Huawei VRP
=====================
This is the vrnetlab docker image for Huawei VRP virtual router simulator.

Building the docker image
-------------------------
You probably can't get the image for this, but if you did, place it in this
directory and run make.

It's been tested to boot and respond to SSH with:

 * Simulator_V100R001C00SPC001T.qcow2  MD5:a4243883628c8ed18b7d5efb39dfee6d 


FUAQ - Frequently or Unfrequently Asked Questions
-------------------------------------------------
##### Q: My VRP isn't starting
A: That's really not a question, is it? Anyway, I've had it take 15 minutes to
start. Sometimes closer to 30 minutes when my machine was loaded.

##### Q: Looking at the trace log, VRP seems to be restarting
A: VRP seems quite sensitive. Disabling CPU throttling has been known to help,
that is, disabling APM in BIOS. Just changing the CPU power governor in Linux
doesn't yield much of a difference. Disabling hyperthreading also helps. While
hyperthreading yields higher concurrency performance, the performance per
thread is actually lowered.
