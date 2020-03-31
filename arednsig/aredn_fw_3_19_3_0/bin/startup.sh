#!/bin/sh
#
# Create a directory in the temporary file system for arednsig dynamic
# data.  Set ownership and permissions to allow the Apache www-data user
# read and write access to this folder.
mkdir /tmp/arednsig
sudo chown :www-data /tmp/arednsig
chmod g+w /tmp/arednsig

# Uncomment the following line if you choose to mount the dynamic
# folder to the folder created above.
#sudo mount --bind /tmp/arednsig  /home/pi/public_html/arednsig/dynamic

# Start arednsig agent
(sleep 5; /home/pi/bin/ardstart;) &

