#! /bin/bash

# SPDX-License-Identifier: MIT
# Largely based on the old ccw_init script.

# This is just a wrapper to migrate old s390 channel-attached network
# device config to the new consolidated persistent configuration with
# chzdev.

DATE=$(date --iso-8601=seconds)

# borrowed from network-scrips, initscripts along with the get_config_by_subchannel
[ -z "$__sed_discard_ignored_files" ] && __sed_discard_ignored_files='/\(~\|\.bak\|\.old\|\.orig\|\.rpmnew\|\.rpmorig\|\.rpmsave\)$/d'

get_configs ()
{
    LANG=C grep -E -i -l \
        "^[[:space:]]*SUBCHANNELS=['\"]?([0-9]\.[0-9]\.[a-f0-9]+)(,[0-9]\.[0-9]\.[a-f0-9]+){1,2}['\"]?([[:space:]]+#|[[:space:]]*$)" \
        /etc/sysconfig/network-scripts/ifcfg-* \
        | LC_ALL=C sed -e "$__sed_discard_ignored_files"
}

get_configs_nm ()
{
    LANG=C grep -E -i -l \
        "^s390-subchannels=([0-9]\.[0-9]\.[a-f0-9]+;){2,3}$" \
        /etc/NetworkManager/system-connections/*.nmconnection \
        | LC_ALL=C sed -e "$__sed_discard_ignored_files"
}

migrate ()
{
# translate variables from the interface config files to OPTIONS
if [ -n "$PORTNAME" ]; then
        if [ "$NETTYPE" = "lcs" ]; then
		OPTIONS="$OPTIONS portno=$PORTNAME"
        else
		OPTIONS="$OPTIONS portname=$PORTNAME"
        fi
fi
if [ "$NETTYPE" = "ctc" -a -n "$CTCPROT" ]; then
	OPTIONS="$OPTIONS protocol=$CTCPROT"
fi

# SUBCHANNELS is only set on mainframe ccwgroup devices
[ -z "$SUBCHANNELS" -o -z "$NETTYPE" ] && return

SUBCHANNELS=$(echo "$SUBCHANNELS" | tr ',' ':')

# shellcheck disable=SC2086
chzdev --enable --persistent "$NETTYPE" "$SUBCHANNELS" $OPTIONS --yes --no-root-update --force --no-settle

# Leave all s390-specifics in original $CONFIG_FILE because NetworkManager
# does something with  NETTYPE, PORTNAME, CTCPROT,  OPTIONS.
# Definitively Leave SUBCHANNELS as it might serve as interface identifier key,
# which is not HWADDR.

echo "znetconfmigrate.sh: Information: Your low-level persistent s390 network device configuration $CONFIG_FILE was migrated to the new consolidated mechanism. From now on, please use lszdev and chzdev from s390utils instead. To finally complete the migration, please run: kdumpctl rebuild; systemctl restart kdump; dracut -f; zipl"

# re-initialize global variables before next possible iteration loop
NETTYPE=""
SUBCHANNELS=""
OPTIONS=""
PORTNAME=""
CTCPROT=""
}

NOLOCALE="yes"

CONFIG_FILES=$(get_configs)
if [ -n "$CONFIG_FILES" ]; then
    for CONFIG_FILE in $CONFIG_FILES; do
	PREFIX="znet.${CONFIG_FILE##*/}.${DATE}.migrated-to-chzdev"
	# show migration output to users and log it into file
	exec > >(tee "$PREFIX.log") 2>&1
	. "$CONFIG_FILE"
	migrate
    done
else
    CONFIG_FILES=$(get_configs_nm)
    for CONFIG_FILE in $CONFIG_FILES; do
	PREFIX="znet.${CONFIG_FILE##*/}.${DATE}.migrated-to-chzdev"
	# show migration output to users and log it into file
	exec > >(tee "$PREFIX.log") 2>&1
	NETTYPE=$(sed -nr "/^\[ethernet\]/ { :l /^s390-nettype[ ]*=/ { s/.*=[ ]*//; p; q;}; n; b l;}" "$CONFIG_FILE")
	SUBCHANNELS=$(sed -nr "/^\[ethernet\]/ { :l /^s390-subchannels[ ]*=/ { s/.*=[ ]*//; p; q;}; n; b l;}" "$CONFIG_FILE" | sed -e "s/;/,/g" -e "s/,$//")
	OPTIONS=$(sed -nr "
/^\[ethernet-s390-options\]/ {
  n # skip matched line with beginning of section
  :l # set label
  /^[^#].*=.*/ { # match non-comment key value line
    p # print
  }
  /^[ ]*\[/ { # match beginning of next section
    q # quit
  }
  n # next
  b l # branch to label
}
" "$CONFIG_FILE")
	migrate
    done
fi
