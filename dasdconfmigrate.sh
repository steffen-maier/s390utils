#!/bin/bash

# SPDX-License-Identifier: MIT
# Copyright IBM Corp. 2023

# This is just a wrapper to migrate old /etc/dasd.conf to the new
# consolidated persistent configuration of s390 devices with chzdev.

CONFIG=/etc/dasd.conf
PATH=/sbin:/bin
export PATH

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

		chzdev --enable --active --persistent dasd "$@" --yes --no-root-update --force --no-settle
		case $? in
		    0)
			# If device exists and could be actively enabled,
			# chzdev could infer the actual dasd device type; done.
			continue
			;;
		esac
		# Configure persistently only to allow migration of
		# configuration for devices that currently do not exist.
		# Chzdev cannot infer the actual dasd device type for an
		# absent device. Therefore, create duplicate configurations
		# for both dasd-eckd and dasd-fba, so either one of them
		# can enable such device when it appears.
		chzdev --enable --persistent dasd-eckd "$@" --yes --no-root-update --force --no-settle
		chzdev --enable --persistent dasd-fba "$@" --yes --no-root-update --force --no-settle
                ;;
        esac
    done
    mv "$CONFIG" "$CONFIG"."$DATE".migrated-to-chzdev
    echo "dasdconfmigrate.sh: Information: Your persistent dasd device configuration file $CONFIG was migrated to the new consolidated mechanism. From now on, please use lszdev and chzdev from s390utils instead. To finally complete the migration, please run: kdumpctl rebuild; systemctl restart kdump; dracut -f; zipl"
fi
