#!/bin/bash

# SPDX-License-Identifier: MIT
# Copyright IBM Corp. 2023

# This is just a wrapper to migrate old /etc/zfcp.conf to the new
# consolidated persistent configuration of s390 devices with chzdev.

CONFIG=/etc/zfcp.conf
PATH=/bin:/sbin

DATE=$(date --iso-8601=seconds)
PREFIX="${CONFIG}.${DATE}.migrated-to-chzdev"

if [ -f "$CONFIG" ]; then
    # show migration output to users and log it into file
    exec > >(tee "${PREFIX}.log") 2>&1
    sed 'y/ABCDEF/abcdef/' < $CONFIG | while read -r line; do
       case $line in
	   \#*) ;;
	   *)
	       [ -z "$line" ] && continue
	       # shellcheck disable=SC2086
	       set -- $line
	       if [ $# -eq 1 ]; then
		   DEVICE=${1##*0x}
		   chzdev --enable --persistent zfcp-host "$DEVICE" --yes --no-root-update --force --no-settle
		   continue
	       fi
	       if [ $# -eq 5 ]; then
		   DEVICE=$1
		   #SCSIID=$2
		   WWPN=$3
		   #SCSILUN=$4
		   FCPLUN=$5
	       elif [ $# -eq 3 ]; then
		   DEVICE=${1##*0x}
		   WWPN=$2
		   FCPLUN=$3
	       fi
	       chzdev --enable --persistent zfcp-lun "$DEVICE:$WWPN:$FCPLUN" --yes --no-root-update --force --no-settle
	       ;;
       esac
   done
   mv "$CONFIG" "$PREFIX"
   echo "zfcpconfmigrate.sh: Information: Your persistent zfcp device configuration file $CONFIG was migrated to the new consolidated mechanism. From now on, please use lszdev and chzdev from s390utils instead. To finally complete the migration, please run: kdumpctl rebuild; systemctl restart kdump; dracut -f; zipl"
fi
