vrnetlab Config Engine lite
===========================
Config Engine lite is a small provisioning system shipped with vrnetlab,
primarily written for three use cases:

 * configure routers in a vrnetlab topology such that the functionality of
   vrnetlab itself can be tested, for example, we want to make sure that
   interfaces are correctly mapped
 * accelerate labing. If you want to do some specific iBGP testing you might
   not be all too interested in setting IP addresses on the 7 routers required
   for your test or configure an entire IGP - use config engine to quickly
   provision the basics and do the rest by hand!
 * serve as inspiration for how you can write a provisioning system running

It's called 'lite' since it doesn't aspire to become a full blown provisioning
system. While it might grow and gain new functionality it will always be
targeted for the requirements of the above, in particular the testing of
vrnetlab itself.

Usage
-----
After building the docker image, you run it like this.

```
docker run -v $(pwd)/templates:/templates -v $(pwd)/topology:/topology --link router1 --link router2 vr-configengine --topo /topology/my-topology.json --xr /templates/xr.j2 --junos /templates/junos.j2 --run
```

 * -v $(pwd)/templates:/templates - Mount a directory containing your templates inside the container
 * -v $(pwd)/topology/topology - Mount a directory containing your topology files inside the container
 * --link router1 --link router2 - Link all routers specified in your topology, enabling config-engine-lite to configure them
 * --topo /topology/my-topology.json - The low level topology built by topology-machine, This references to the /topology mountpoint
 * --xr /templates/xr.j2 - Configuration template for ios-xr, this references to the /templates mountpoint
 * --junos /templates/junos.j2 - Configuration template for JunOS, this refrences to the /templates mountpoint
 * --run - Actually deploy the configuration. If this is not specified, the configuration changes will not be committed and config diff will be printed.
