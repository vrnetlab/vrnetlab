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
