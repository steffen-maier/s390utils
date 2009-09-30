#!/bin/bash

# config file syntax:
# deviceno   WWPN   FCPLUN
#
# Example:
# 0.0.4000 0x5005076300C213e9 0x5022000000000000 
# 0.0.4001 0x5005076300c213e9 0x5023000000000000 
#
#
# manual setup:
# modprobe zfcp
# echo 1    > /sys/bus/ccw/drivers/zfcp/0.0.4000/online
# echo LUN  > /sys/bus/ccw/drivers/zfcp/0.0.4000/WWPN/unit_add
# 
# Example:
# modprobe zfcp
# echo 1                  > /sys/bus/ccw/drivers/zfcp/0.0.4000/online
# echo 0x5022000000000000 > /sys/bus/ccw/drivers/zfcp/0.0.4000/0x5005076300c213e9/unit_add

CONFIG=/etc/zfcp.conf
PATH=/bin:/usr/bin:/sbin:/usr/sbin

if [ -f "$CONFIG" ]; then

   if [ ! -d /sys/bus/ccw/drivers/zfcp ]; then
      modprobe zfcp
   fi
   if [ ! -d /sys/bus/ccw/drivers/zfcp ]; then
      return
   fi
   cat $CONFIG | grep -v "^#" | tr "A-Z" "a-z" | while read line; do
      numparams=$(echo $line | wc -w)
      if [ $numparams == 5 ]; then
         read DEVICE SCSIID WWPN SCSILUN FCPLUN < <(echo $line)
         echo "Warning: Deprecated values in /etc/zfcp.conf, ignoring SCSI ID $SCSIID and SCSI LUN $SCSILUN"
      elif [ $numparams == 3 ]; then
         read DEVICE WWPN FCPLUN < <(echo $line)
      fi
      echo 1 > /sys/bus/ccw/drivers/zfcp/${DEVICE/0x/}/online
      [ ! -d /sys/bus/ccw/drivers/zfcp/${DEVICE/0x/}/$WWPN/$FCPLUN ] && echo $FCPLUN > /sys/bus/ccw/drivers/zfcp/${DEVICE/0x/}/$WWPN/unit_add
   done
fi
