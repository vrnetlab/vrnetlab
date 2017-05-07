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
After building the docker image, you run it like this. There are two modes of operation, topology mode and single-router-mode. 


### Topology mode
Use config-engine-lite and jinja2 templates to configure your topomachine topology.
```
docker run -v $(pwd)/templates:/templates -v $(pwd)/topology:/topology --link router1 --link router2 vr-configengine --topo /topology/lltopo.json --xr /templates/xr.j2 --junos /templates/junos.j2 --run
```

 * -v $(pwd)/templates:/templates - Mount a directory containing your templates inside the container
 * -v $(pwd)/topology/topology - Mount a directory containing your topology files inside the container
 * --link router1 --link router2 - Link all routers specified in your topology, enabling config-engine-lite to configure them
 * --topo /topology/lltopo.json - The low level topology built by topology-machine, This references to the /topology mountpoint
 * --ios /templates/ios.j2 - Configuration template for IOS (CSR 1000v), this references to the /templates mountpoint
 * --xr /templates/xr.j2 - Configuration template for ios-xr, this references to the /templates mountpoint
 * --junos /templates/junos.j2 - Configuration template for JunOS, this refrences to the /templates mountpoint
 * --run - Actually deploy the configuration. If this is not specified, the configuration changes will not be committed and config diff will be printed.

### Single-router mode
Apply a configuration template to a single router, useful for bootstrapping a router for use with vr-bgp for instance.
```
docker run -v $(pwd)/templates:/templates --link router1 vr-configengine --type xrv --router router1 --config /templates/router1.j2 --attrs "key1=value1,key2=value2"
```
 * -v $(pwd)/templates:/templates - Mount a directory containing your templates inside the container
 * --link router1 - Link the router you want to configure
 * --config /templates/router1.j2 - Your router configuration, references /templates moutpoint
 * --type vmx - Type of router to configure (valid values are vmx, xrv and csr)
 * --attr "key=value" - A key/value pair available in the template, can be specified multiple times.

### Common parameters
These parameters are available in both modes
 * --wait-for-boot - Block until we can connect to the router via SSH. If neither --diff or --run is used this option will simply block until all your routers are started
 * --diff - Print configuration diff and discard the configuration
 * --run - Commit the configuration to the router
