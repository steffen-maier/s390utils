# secure boot support is for RHEL only
%if 0%{?rhel} >= 8
%global signzipl 1
%endif

Name:           s390utils
Summary:        Utilities and daemons for IBM z Systems
Version:        2.16.0
Release:        2%{?dist}
Epoch:          2
License:        MIT
ExclusiveArch:  s390 s390x
#URL:            http://www.ibm.com/developerworks/linux/linux390/s390-tools.html
URL:            https://github.com/ibm-s390-tools/s390-tools
Source0:        https://github.com/ibm-s390-tools/s390-tools/archive/v%{version}.tar.gz#/s390-tools-%{version}.tar.gz
Source5:        zfcpconf.sh
Source7:        zfcp.udev
# files for DASD initialization
Source12:       dasd.udev
Source13:       dasdconf.sh
Source14:       device_cio_free
Source15:       device_cio_free.service
Source16:       ccw_init
Source17:       ccw.udev
Source21:       normalize_dasd_arg
Source23:       20-zipl-kernel.install
Source24:       52-zipl-rescue.install
Source25:       91-zipl.install

%if 0%{?signzipl}
%define pesign_name redhatsecureboot302
%endif

# change the defaults to match Fedora environment
Patch0:         s390-tools-zipl-invert-script-options.patch
Patch1:         s390-tools-zipl-blscfg-rpm-nvr-sort.patch

# upstream fixes
# https://github.com/ibm-s390-linux/s390-tools/commit/3f3f063c98278f53ad3b34e68b70fca62eaea8fb
Patch100:       s390-tools-2.16.0-zkey.patch
# https://github.com/ibm-s390-linux/s390-tools/commit/b6bdd7744aba06d82f30b0c84012f0b06ccb01de
Patch101:       s390-tools-2.16.0-genprotimg.patch

Requires:       s390utils-core = %{epoch}:%{version}-%{release}
Requires:       s390utils-base = %{epoch}:%{version}-%{release}
Requires:       s390utils-osasnmpd = %{epoch}:%{version}-%{release}
Requires:       s390utils-cpuplugd = %{epoch}:%{version}-%{release}
Requires:       s390utils-mon_statd = %{epoch}:%{version}-%{release}
Requires:       s390utils-iucvterm = %{epoch}:%{version}-%{release}
Requires:       s390utils-ziomon = %{epoch}:%{version}-%{release}

BuildRequires: make
BuildRequires:  gcc-c++

%description
This is a meta package for installing the default s390-tools sub packages.
If you do not need all default sub packages, it is recommended to install the
required sub packages separately.

The s390utils packages contain a set of user space utilities that should to
be used together with the zSeries (s390) Linux kernel and device drivers.

%prep
%setup -q -n s390-tools-%{version}

# Fedora/RHEL changes
%patch0 -p1 -b .zipl-invert-script-options
%patch1 -p1 -b .blscfg-rpm-nvr-sort

# upstream fixes
%patch100 -p1
%patch101 -p1

# remove --strip from install
find . -name Makefile | xargs sed -i 's/$(INSTALL) -s/$(INSTALL)/g'


%build
make \
        CFLAGS="%{build_cflags}" CXXFLAGS="%{build_cflags}" LDFLAGS="%{build_ldflags}" \
        BINDIR=/usr/sbin \
        DISTRELEASE=%{release} \
        V=1


%install
make install \
        HAVE_DRACUT=1 \
        DESTDIR=%{buildroot} \
        BINDIR=/usr/sbin \
        SYSTEMDSYSTEMUNITDIR=%{_unitdir} \
        DISTRELEASE=%{release} \
        V=1

# sign the stage3 bootloader
%if 0%{?signzipl}
if [ -x /usr/bin/rpm-sign ]; then
    pushd %{buildroot}/lib/s390-tools/
        rpm-sign --key "%{pesign_name}" --lkmsign stage3.bin --output stage3.signed
        mv stage3.signed stage3.bin
    popd
else
    echo "rpm-sign not available, stage3 won't be signed"
fi
%endif

# move tools to searchable dir
mv %{buildroot}%{_datadir}/s390-tools/netboot/mk-s390image %{buildroot}%{_bindir}

mkdir -p %{buildroot}{/boot,%{_udevrulesdir},%{_sysconfdir}/{profile.d,sysconfig},%{_prefix}/lib/modules-load.d}
install -p -m 644 zipl/boot/tape0.bin %{buildroot}/boot/tape0
install -p -m 755 %{SOURCE5} %{buildroot}%{_sbindir}
install -p -m 755 %{SOURCE13} %{buildroot}%{_sbindir}
install -p -m 755 %{SOURCE21} %{buildroot}%{_sbindir}
install -p -m 644 %{SOURCE7} %{buildroot}%{_udevrulesdir}/56-zfcp.rules
install -p -m 644 %{SOURCE12} %{buildroot}%{_udevrulesdir}/56-dasd.rules

touch %{buildroot}%{_sysconfdir}/{zfcp.conf,dasd.conf}

# upstream udev rules
install -Dp -m 644 etc/udev/rules.d/*.rules %{buildroot}%{_udevrulesdir}

# upstream modules config
install -Dp -m 644 etc/modules-load.d/*.conf %{buildroot}%{_prefix}/lib/modules-load.d

# Install kernel-install scripts
install -d -m 0755 %{buildroot}%{_prefix}/lib/kernel/install.d/
install -D -m 0755 -t %{buildroot}%{_prefix}/lib/kernel/install.d/ zfcpdump/10-zfcpdump.install
install -D -m 0755 -t %{buildroot}%{_prefix}/lib/kernel/install.d/ %{SOURCE23}
install -D -m 0755 -t %{buildroot}%{_prefix}/lib/kernel/install.d/ %{SOURCE24}
install -D -m 0755 -t %{buildroot}%{_prefix}/lib/kernel/install.d/ %{SOURCE25}
install -d -m 0755 %{buildroot}%{_sysconfdir}/kernel/install.d/
install -m 0644 /dev/null %{buildroot}%{_sysconfdir}/kernel/install.d/20-grubby.install

# install usefull headers for devel subpackage
mkdir -p %{buildroot}%{_includedir}/%{name}
install -p -m 644 include/lib/vtoc.h %{buildroot}%{_includedir}/%{name}

# device_cio_free
install -p -m 755 %{SOURCE14} %{buildroot}%{_sbindir}
pushd %{buildroot}%{_sbindir}
for lnk in dasd zfcp znet; do
    ln -sf device_cio_free ${lnk}_cio_free
done
popd
install -p -m 644 %{SOURCE15} %{buildroot}%{_unitdir}

# ccw
install -p -m 755 %{SOURCE16} %{buildroot}/usr/lib/udev/ccw_init
install -p -m 644 %{SOURCE17} %{buildroot}%{_udevrulesdir}/81-ccw.rules

# zipl.conf to be ghosted
touch %{buildroot}%{_sysconfdir}/zipl.conf


%files
%doc README.md

#
# ************************* s390-tools core package  *************************
#
%package core
License:        MIT
Summary:        S390 core tools
Requires:       coreutils
%{?systemd_requires}
# BRs are covered via the base package


%description core
This package provides minimal set of tools needed to system to boot.

%post core
%systemd_post device_cio_free.service
%systemd_post cpi.service

%preun core
%systemd_preun device_cio_free.service
%systemd_preun cpi.service

%postun core
%systemd_postun_with_restart cpi.service

%files core
%doc README.md zdev/src/chzdev_usage.txt
%doc LICENSE
%{_sbindir}/chreipl
%{_sbindir}/chzdev
%{_sbindir}/cio_ignore
%{_sbindir}/dasdfmt
%{_sbindir}/dasdinfo
%{_sbindir}/fdasd
%{_sbindir}/lszdev
%{_sbindir}/zipl
%dir /lib/s390-tools/
/lib/s390-tools/{zipl,chreipl}_helper.*
/lib/s390-tools/cpictl
/lib/s390-tools/stage3.bin
/lib/s390-tools/zdev-root-update
/lib/s390-tools/zipl.conf
%ghost %config(noreplace) %{_sysconfdir}/zipl.conf
%{_unitdir}/cpi.service
%config(noreplace) %{_sysconfdir}/sysconfig/cpi
/usr/lib/dracut/modules.d/95zdev/
%{_mandir}/man5/zipl.conf.5*
%{_mandir}/man8/chreipl.8*
%{_mandir}/man8/chzdev.8*
%{_mandir}/man8/cio_ignore.8*
%{_mandir}/man8/dasdfmt.8*
%{_mandir}/man8/dasdinfo.8*
%{_mandir}/man8/fdasd.8*
%{_mandir}/man8/lszdev.8*
%{_mandir}/man8/zipl.8*

# Additional Fedora/RHEL specific stuff
%ghost %config(noreplace) %{_sysconfdir}/dasd.conf
%ghost %config(noreplace) %{_sysconfdir}/zfcp.conf
%{_sbindir}/dasdconf.sh
%{_sbindir}/normalize_dasd_arg
%{_sbindir}/zfcpconf.sh
%{_sbindir}/device_cio_free
%{_sbindir}/dasd_cio_free
%{_sbindir}/zfcp_cio_free
%{_sbindir}/znet_cio_free
%{_unitdir}/device_cio_free.service
/usr/lib/udev/ccw_init
%{_udevrulesdir}/40-z90crypt.rules
%{_udevrulesdir}/56-dasd.rules
%{_udevrulesdir}/56-zfcp.rules
%{_udevrulesdir}/59-dasd.rules
%{_udevrulesdir}/60-readahead.rules
%{_udevrulesdir}/81-ccw.rules
%{_udevrulesdir}/90-cpi.rules
%{_sysconfdir}/kernel/install.d/20-grubby.install
%{_prefix}/lib/kernel/install.d/10-zfcpdump.install
%{_prefix}/lib/kernel/install.d/20-zipl-kernel.install
%{_prefix}/lib/kernel/install.d/52-zipl-rescue.install
%{_prefix}/lib/kernel/install.d/91-zipl.install
%{_prefix}/lib/modules-load.d/s390-pkey.conf

#
# *********************** s390-tools base package  ***********************
#

%package base
License:        MIT
Summary:        S390 base tools
Requires:       gawk sed coreutils
Requires:       sg3_utils
Requires:       ethtool
Requires:       tar
Requires:       s390utils-core = %{epoch}:%{version}-%{release}
%{?systemd_requires}
BuildRequires:  perl-generators
BuildRequires:  ncurses-devel
BuildRequires:  glibc-static
BuildRequires:  cryptsetup-devel >= 2.0.3
BuildRequires:  json-c-devel
BuildRequires:  rpm-devel
BuildRequires:  glib2-devel


%description base
s390 base tools. This collection provides the following utilities:
   * dasdfmt:
     Low-level format ECKD DASDs with the classical linux disk layout or the
     new z/OS compatible disk layout.

   * fdasd:
     Create or modify partitions on ECKD DASDs formatted with the z/OS
     compatible disk layout.

   * dasdview:
     Display DASD and VTOC information or dump the contents of a DASD to the
     console.

   * dasdinfo:
     Display unique DASD ID, either UID or volser.

   * udev rules:
     - 59-dasd.rules: rules for unique DASD device nodes created in /dev/disk/.

   * zipl:
     Make DASDs or tapes bootable for system IPL or system dump.

   * zgetdump:
     Retrieve system dumps from either tapes or DASDs.

   * qetharp:
     Read and flush the ARP cache on OSA Express network cards.

   * tape390_display:
     Display information on the message display facility of a zSeries tape
     device.

   * tape390_crypt:
     Control and query crypto settings for 3592 zSeries tape devices.

   * qethconf:
     bash shell script simplifying the usage of qeth IPA (IP address
     takeover), VIPA (Virtual IP address) and Proxy ARP.

   * dbginfo.sh:
     Shell script collecting useful information about the current system for
     debugging purposes.

   * zfcpdump:
     Dump tool to create system dumps on fibre channel attached SCSI disks.
     It is installed using the zipl command.

   * zfcpdump_v2:
     Version 2 of the zfcpdump tool. Now based on the upstream 2.6.26 Linux
     kernel.

   * ip_watcher:
     Provides HiperSockets Network Concentrator functionality.
     It looks for addresses in the HiperSockets and sets them as Proxy ARP
     on the OSA cards. It also adds routing entries for all IP addresses
     configured on active HiperSockets devices.
     Use start_hsnc.sh to start HiperSockets Network Concentrator.

   * tunedasd:
     Adjust tunable parameters on DASD devices.

   * vmconvert:
     Convert system dumps created by the z/VM VMDUMP command into dumps with
     LKCD format. These LKCD dumps can then be analyzed with the dump analysis
     tool lcrash.

   * vmcp:
     Allows Linux users to send commands to the z/VM control program (CP).
     The normal usage is to invoke vmcp with the command you want to
     execute. The response of z/VM is written to the standard output.

   * vmur:
     Allows to work with z/VM spool file queues (reader, punch, printer).

   * zfcpdbf:
     Display debug data of zfcp. zfcp provides traces via the s390 debug
     feature. Those traces are filtered with the zfcpdbf script, i.e. merge
     several traces, make it more readable etc.

   * scsi_logging_level:
     Create, get or set the logging level for the SCSI logging facility.

   * zconf:
     Set of scripts to configure and list status information of Linux for
     zSeries IO devices.
     - chccwdev:   Modify generic attributes of channel attached devices.
     - lscss:      List channel subsystem devices.
     - lsdasd:     List channel attached direct access storage devices (DASD).
     - lsqeth:     List all qeth-based network devices with their corresponding
                   settings.
     - lstape:     List tape devices, both channel and FCP attached.
     - lszfcp:     Shows information contained in sysfs about zfcp adapters,
                   ports and units that are online.
     - lschp:      List information about available channel-paths.
     - chchp:      Modify channel-path state.
     - lsluns:     List available SCSI LUNs depending on adapter or port.
     - lszcrypt:   Show Information about zcrypt devices and configuration.
     - chzcrypt:   Modify zcrypt configuration.
     - znetconf:   List and configure network devices for System z network
                   adapters.
     - cio_ignore: Query and modify the contents of the CIO device driver
                   blacklist.

   * dumpconf:
     Allows to configure the dump device used for system dump in case a kernel
     panic occurs. This tool can also be used as an init script for etc/init.d.
     Prerequisite for dumpconf is a Linux kernel with the "dump on panic"
     feature.

   * ipl_tools:
     Tools set to configure and list reipl and shutdown actions.
     - lsreipl: List information of reipl device.
     - chreipl: Change reipl device settings.
     - lsshut:  List actions which will be done in case of halt, poff, reboot
                or panic.
     - chshut:  Change actions which should be done in case of halt, poff,
                reboot or panic.

   * cpi:
    Allows to set the system and sysplex names from the Linux guest to
    the HMC/SE using the Control Program Identification feature.

   * genprotimg:
    Tool for the creation of PV images. The image consists of a concatenation of
    a plain text boot loader, the encrypted components for kernel, initrd, and
    cmdline, and the integrity-protected PV header, containing metadata necessary for
    running the guest in PV mode. Protected VMs (PVM) are KVM VMs, where KVM can't
    access the VM's state like guest memory and guest registers anymore.

For more information refer to the following publications:
   * "Device Drivers, Features, and Commands" chapter "Useful Linux commands"
   * "Using the dump tools"

%pre base
# check for zkeyadm group and create it
getent group zkeyadm > /dev/null || groupadd -r zkeyadm

%post base
%systemd_post dumpconf.service

%preun base
%systemd_preun dumpconf.service

%postun base
%systemd_postun_with_restart dumpconf.service

%files base
%doc README.md zdev/src/lszdev_usage.txt
%{_sbindir}/chccwdev
%{_sbindir}/chchp
%{_sbindir}/chcpumf
%{_sbindir}/chshut
%{_sbindir}/chzcrypt
%{_sbindir}/dasdstat
%{_sbindir}/dasdview
%{_sbindir}/dbginfo.sh
%{_sbindir}/hsci
%{_sbindir}/hyptop
%{_sbindir}/ip_watcher.pl
%{_sbindir}/lschp
%{_sbindir}/lscpumf
%{_sbindir}/lscss
%{_sbindir}/lsdasd
%{_sbindir}/lsqeth
%{_sbindir}/lsluns
%{_sbindir}/lsreipl
%{_sbindir}/lsscm
%{_sbindir}/lsshut
%{_sbindir}/lsstp
%{_sbindir}/lstape
%{_sbindir}/lszcrypt
%{_sbindir}/lszfcp
%{_sbindir}/qetharp
%{_sbindir}/qethconf
%{_sbindir}/qethqoat
%{_sbindir}/scsi_logging_level
%{_sbindir}/start_hsnc.sh
%{_sbindir}/tape390_crypt
%{_sbindir}/tape390_display
%{_sbindir}/ttyrun
%{_sbindir}/tunedasd
%{_sbindir}/vmcp
%{_sbindir}/vmur
%{_sbindir}/xcec-bridge
%{_sbindir}/zcryptctl
%{_sbindir}/zcryptstats
%{_sbindir}/zfcpdbf
%{_sbindir}/zgetdump
%{_sbindir}/zipl-switch-to-blscfg
%{_sbindir}/znetconf
%{_sbindir}/zpcictl
%{_bindir}/dump2tar
%{_bindir}/genprotimg
%{_bindir}/mk-s390image
%{_bindir}/vmconvert
%{_bindir}/zkey
%{_bindir}/zkey-cryptsetup
%{_unitdir}/dumpconf.service
%ghost %config(noreplace) %{_sysconfdir}/zipl.conf
%config(noreplace) %{_sysconfdir}/sysconfig/dumpconf
/lib/s390-tools/dumpconf
/lib/s390-tools/lsznet.raw
%dir /lib/s390-tools/zfcpdump
/lib/s390-tools/zfcpdump/zfcpdump-initrd
/lib/s390-tools/znetcontrolunits
%{_libdir}/libekmfweb.so.*
%{_libdir}/zkey/zkey-ekmfweb.so
%{_mandir}/man1/dbginfo.sh.1*
%{_mandir}/man1/dump2tar.1*
%{_mandir}/man1/lscpumf.1*
%{_mandir}/man1/vmconvert.1*
%{_mandir}/man1/zfcpdbf.1*
%{_mandir}/man1/zipl-switch-to-blscfg.1*
%{_mandir}/man1/zkey.1*
%{_mandir}/man1/zkey-cryptsetup.1*
%{_mandir}/man1/zkey-ekmfweb.1*
%{_mandir}/man4/prandom.4*
%{_mandir}/man8/chccwdev.8*
%{_mandir}/man8/chchp.8*
%{_mandir}/man8/chcpumf.8*
%{_mandir}/man8/chshut.8*
%{_mandir}/man8/chzcrypt.8*
%{_mandir}/man8/dasdstat.8*
%{_mandir}/man8/dasdview.8*
%{_mandir}/man8/dumpconf.8*
%{_mandir}/man8/genprotimg.8.*
%{_mandir}/man8/hsci.8*
%{_mandir}/man8/hyptop.8*
%{_mandir}/man8/lschp.8*
%{_mandir}/man8/lscss.8*
%{_mandir}/man8/lsdasd.8*
%{_mandir}/man8/lsluns.8*
%{_mandir}/man8/lsqeth.8*
%{_mandir}/man8/lsreipl.8*
%{_mandir}/man8/lsscm.8*
%{_mandir}/man8/lsshut.8*
%{_mandir}/man8/lsstp.8*
%{_mandir}/man8/lstape.8*
%{_mandir}/man8/lszcrypt.8*
%{_mandir}/man8/lszfcp.8*
%{_mandir}/man8/qetharp.8*
%{_mandir}/man8/qethconf.8*
%{_mandir}/man8/qethqoat.8*
%{_mandir}/man8/tape390_crypt.8*
%{_mandir}/man8/tape390_display.8*
%{_mandir}/man8/ttyrun.8*
%{_mandir}/man8/tunedasd.8*
%{_mandir}/man8/vmcp.8*
%{_mandir}/man8/vmur.8*
%{_mandir}/man8/zcryptctl.8*
%{_mandir}/man8/zcryptstats.8*
%{_mandir}/man8/zgetdump.8*
%{_mandir}/man8/znetconf.8*
%{_mandir}/man8/zpcictl.8*
%dir %{_datadir}/s390-tools/
%{_datadir}/s390-tools/genprotimg/
%{_datadir}/s390-tools/netboot/
%dir %attr(0770,root,zkeyadm) %{_sysconfdir}/zkey
%dir %attr(0770,root,zkeyadm) %{_sysconfdir}/zkey/repository
%config(noreplace) %attr(0660,root,zkeyadm)%{_sysconfdir}/zkey/kms-plugins.conf

# Additional Fedora/RHEL specific stuff
/boot/tape0

#
# *********************** s390-tools osasnmpd package  ***********************
#
%package osasnmpd
Summary:        SNMP sub-agent for OSA-Express cards
Requires:       net-snmp
Requires:       psmisc
BuildRequires:  net-snmp-devel

%description osasnmpd
UCD-SNMP/NET-SNMP sub-agent implementing MIBs provided by OSA-Express
features Fast Ethernet, Gigabit Ethernet, High Speed Token Ring and
ATM Ethernet LAN Emulation in QDIO mode.

%files osasnmpd
%{_sbindir}/osasnmpd
%{_udevrulesdir}/57-osasnmpd.rules
%{_mandir}/man8/osasnmpd.8*

#
# *********************** s390-tools mon_statd package  **********************
#
%package mon_statd
Summary:         Monitoring daemons for Linux in z/VM
Requires:        coreutils
%{?systemd_requires}

%description mon_statd
Monitoring daemons for Linux in z/VM:

  - mon_fsstatd: Daemon that writes file system utilization data to the
                 z/VM monitor stream.

  - mon_procd:   Daemon that writes process information data to the z/VM
                 monitor stream.

%post mon_statd
%systemd_post mon_fsstatd.service
%systemd_post mon_procd.service

%preun mon_statd
%systemd_preun mon_fsstatd.service
%systemd_preun mon_procd.service

%postun mon_statd
%systemd_postun_with_restart mon_fsstatd.service
%systemd_postun_with_restart mon_procd.service

%files mon_statd
%{_sbindir}/mon_fsstatd
%{_sbindir}/mon_procd
%config(noreplace) %{_sysconfdir}/sysconfig/mon_fsstatd
%config(noreplace) %{_sysconfdir}/sysconfig/mon_procd
%{_unitdir}/mon_fsstatd.service
%{_unitdir}/mon_procd.service
%{_mandir}/man8/mon_fsstatd.8*
%{_mandir}/man8/mon_procd.8*

#
# *********************** s390-tools cpuplugd package  ***********************
#
%package cpuplugd
Summary:         Daemon that manages CPU and memory resources
%{?systemd_requires}
BuildRequires: systemd

%description cpuplugd
Daemon that manages CPU and memory resources based on a set of rules.
Depending on the workload CPUs can be enabled or disabled. The amount of
memory can be increased or decreased exploiting the CMM1 feature.

%post cpuplugd
%systemd_post cpuplugd.service

%preun cpuplugd
%systemd_preun cpuplugd.service

%postun cpuplugd
%systemd_postun_with_restart cpuplugd.service

%files cpuplugd
%config(noreplace) %{_sysconfdir}/cpuplugd.conf
%{_sbindir}/cpuplugd
%{_mandir}/man5/cpuplugd.conf.5*
%{_mandir}/man8/cpuplugd.8*
%{_unitdir}/cpuplugd.service

#
# *********************** s390-tools ziomon package  *************************
#
%package ziomon
Summary:        S390 ziomon tools
Requires:       blktrace
Requires:       coreutils
Requires:       device-mapper-multipath
Requires:       gawk
Requires:       grep
Requires:       lsscsi
Requires:       procps-ng
Requires:       rsync
Requires:       sed
Requires:       tar
Requires:       util-linux

%description ziomon
Tool set to collect data for zfcp performance analysis and report.

%files ziomon
%{_sbindir}/ziomon
%{_sbindir}/ziomon_fcpconf
%{_sbindir}/ziomon_mgr
%{_sbindir}/ziomon_util
%{_sbindir}/ziomon_zfcpdd
%{_sbindir}/ziorep_config
%{_sbindir}/ziorep_traffic
%{_sbindir}/ziorep_utilization
%{_mandir}/man8/ziomon.8*
%{_mandir}/man8/ziomon_fcpconf.8*
%{_mandir}/man8/ziomon_mgr.8*
%{_mandir}/man8/ziomon_util.8*
%{_mandir}/man8/ziomon_zfcpdd.8*
%{_mandir}/man8/ziorep_config.8*
%{_mandir}/man8/ziorep_traffic.8*
%{_mandir}/man8/ziorep_utilization.8*

#
# *********************** s390-tools iucvterm package  *************************
#
%package iucvterm
Summary:        z/VM IUCV terminal applications
Requires(pre):  shadow-utils
Requires(post): grep
Requires(postun): grep
BuildRequires:  gettext
BuildRequires: systemd

%description iucvterm
A set of applications to provide terminal access via the z/VM Inter-User
Communication Vehicle (IUCV). The terminal access does not require an
active TCP/IP connection between two Linux guest operating systems.

- iucvconn:  Application to establish a terminal connection via z/VM IUCV.
- iucvtty:   Application to provide terminal access via z/VM IUCV.
- ts-shell:  Terminal server shell to authorize and control IUCV terminal
             connections for individual Linux users.

%pre iucvterm
# check for ts-shell group and create it
getent group ts-shell > /dev/null || groupadd -r ts-shell

%post iucvterm
# /etc/shells is provided by "setup"
grep -q '^/usr/bin/ts-shell$' /etc/shells \
    || echo "/usr/bin/ts-shell" >> /etc/shells

%postun iucvterm
if [ $1 = 0 ]
then
    # remove ts-shell from /etc/shells on uninstall
    grep -v '^/usr/bin/ts-shell$' /etc/shells > /etc/shells.ts-new
    mv /etc/shells.ts-new /etc/shells
    chmod 0644 /etc/shells
fi

%files iucvterm
%dir %{_sysconfdir}/iucvterm
%config(noreplace) %attr(0640,root,ts-shell) %{_sysconfdir}/iucvterm/ts-audit-systems.conf
%config(noreplace) %attr(0640,root,ts-shell) %{_sysconfdir}/iucvterm/ts-authorization.conf
%config(noreplace) %attr(0640,root,ts-shell) %{_sysconfdir}/iucvterm/ts-shell.conf
%config(noreplace) %attr(0640,root,ts-shell) %{_sysconfdir}/iucvterm/unrestricted.conf
%{_bindir}/iucvconn
%{_bindir}/iucvtty
%{_bindir}/ts-shell
%{_sbindir}/chiucvallow
%{_sbindir}/lsiucvallow
%dir %attr(2770,root,ts-shell) /var/log/ts-shell
%doc iucvterm/doc/ts-shell
%{_mandir}/man1/iucvconn.1*
%{_mandir}/man1/iucvtty.1*
%{_mandir}/man1/ts-shell.1*
%{_mandir}/man7/af_iucv.7*
%{_mandir}/man8/chiucvallow.8*
%{_mandir}/man9/hvc_iucv.9*
%{_unitdir}/iucvtty-login@.service
%{_unitdir}/ttyrun-getty@.service


#
# *********************** cmsfs-fuse package  ***********************
#
%package cmsfs-fuse
Summary:        CMS file system based on FUSE
BuildRequires:  fuse-devel
Requires:       fuse
Obsoletes:      %{name}-cmsfs < 2:2.7.0-3

%description cmsfs-fuse
This package contains the CMS file system based on FUSE.

%files cmsfs-fuse
%dir %{_sysconfdir}/cmsfs-fuse
%config(noreplace) %{_sysconfdir}/cmsfs-fuse/filetypes.conf
%{_bindir}/cmsfs-fuse
%{_mandir}/man1/cmsfs-fuse.1*

#
# *********************** zdsfs package  ***********************
#
%package zdsfs
Summary:        z/OS data set access based on FUSE
BuildRequires:  fuse-devel
BuildRequires:  libcurl-devel
Requires:       fuse

%description zdsfs
This package contains the z/OS data set access based on FUSE.

%files zdsfs
%{_bindir}/zdsfs
%{_mandir}/man1/zdsfs.1*

#
# *********************** hmcdrvfs package  ***********************
#
%package hmcdrvfs
Summary:       HMC drive file system based on FUSE
BuildRequires: fuse-devel
Requires:      fuse

%description hmcdrvfs
This package contains a HMC drive file system based on FUSE and a tool
to list files and directories.

%files hmcdrvfs
%{_bindir}/hmcdrvfs
%{_sbindir}/lshmc
%{_mandir}/man1/hmcdrvfs.1*
%{_mandir}/man8/lshmc.8*

#
# *********************** cpacfstatsd package  ***********************
#
%package cpacfstatsd
Summary:       Monitor and maintain CPACF activity counters
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd
Requires(pre): shadow-utils
BuildRequires: systemd

%description cpacfstatsd
The cpacfstats tools provide a client/server application set to monitor
and maintain CPACF activity counters.

%post cpacfstatsd
%systemd_post cpacfstatsd.service

%preun cpacfstatsd
%systemd_preun cpacfstatsd.service

%postun cpacfstatsd
%systemd_postun_with_restart cpacfstatsd.service

%pre cpacfstatsd
getent group cpacfstats >/dev/null || groupadd -r cpacfstats

%files cpacfstatsd
%{_bindir}/cpacfstats
%{_sbindir}/cpacfstatsd
%{_mandir}/man1/cpacfstats.1*
%{_mandir}/man8/cpacfstatsd.8*
%{_unitdir}/cpacfstatsd.service

#
# *********************** devel package  ***********************
#
%package devel
Summary:        Development files

Requires: %{name}-base%{?_isa} = %{epoch}:%{version}-%{release}

%description devel
User-space development files for the s390/s390x architecture.

%files devel
%{_includedir}/%{name}/
%{_includedir}/ekmfweb/
%{_libdir}/libekmfweb.so


%changelog
* Mon Mar 01 2021 Dan Horák <dan[at]danny.cz> - 2:2.16.0-2
- drop superfluous Require from s390utils-base

* Wed Feb 24 2021 Dan Horák <dan[at]danny.cz> - 2:2.16.0-1
- rebased to 2.16.0

* Wed Jan 27 2021 Fedora Release Engineering <releng@fedoraproject.org> - 2:2.15.1-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_34_Mass_Rebuild

* Tue Jan 05 2021 Dan Horák <dan[at]danny.cz> - 2:2.15.1-4
- move lszdev to core

* Mon Jan 04 2021 Dan Horák <dan[at]danny.cz> - 2:2.15.1-3
- move fdasd to core

* Thu Oct 29 2020 Petr Šabata <contyk@redhat.com> - 2:2.15.1-2
- Fix the development package dependency by adding epoch

* Thu Oct 29 2020 Dan Horák <dan[at]danny.cz> - 2:2.15.1-1
- rebased to 2.15.1

* Wed Oct 28 2020 Dan Horák <dan[at]danny.cz> - 2:2.15.0-2
- move mk-s390image to /usr/bin

* Tue Oct 27 2020 Dan Horák <dan[at]danny.cz> - 2:2.15.0-1
- rebased to 2.15.0

* Wed Oct 07 2020 Dan Horák <dan[at]danny.cz> - 2:2.14.0-4
- update scripts for https://fedoraproject.org/wiki/Changes/NetworkManager_keyfile_instead_of_ifcfg_rh

* Mon Sep 21 2020 Dan Horák <dan[at]danny.cz> - 2:2.14.0-3
- rebuilt for net-snmp 5.9

* Wed Aug 26 2020 Dan Horák <dan[at]danny.cz> - 2:2.14.0-2
- add support for auto LUN scan to zfcpconf.sh (#1552697)

* Tue Aug 25 2020 Dan Horák <dan[at]danny.cz> - 2:2.14.0-1
- rebased to 2.14.0

* Wed Jul 29 2020 Fedora Release Engineering <releng@fedoraproject.org> - 2:2.13.0-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_33_Mass_Rebuild

* Fri Jul 03 2020 Javier Martinez Canillas <javierm@redhat.com> - 2:2.13.0-4
- add a default entry in zipl.conf if there isn't one present (#1698363)

* Tue Jun 09 2020 Jakub Čajka <jcajka@redhat.com> - 2:2.13.0-3
- split off core package with basic functionalities and reduced deps from base sub-package

* Mon Jun 01 2020 Dan Horák <dan[at]danny.cz> - 2:2.13.0-2
- avoid dependency on network-scripts (part of PR #4)

* Mon May 11 2020 Dan Horák <dan[at]danny.cz> - 2:2.13.0-1
- rebased to 2.13.0

* Wed Apr 22 2020 Dan Horák <dan@danny.cz> - 2:2.12.0-4
- rebuilt for json-c soname bump

* Thu Jan 30 2020 Fedora Release Engineering <releng@fedoraproject.org> - 2:2.12.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_32_Mass_Rebuild

* Tue Jan 14 2020 Dan Horák <dan[at]danny.cz> - 2:2.12.0-2
- fix service order after switching to real root file system (#1790496, #1790790)

* Mon Jan 06 2020 Dan Horák <dan[at]danny.cz> - 2:2.12.0-1
- rebased to 2.12.0

* Fri Dec 13 2019 Dan Horák <dan[at]danny.cz> - 2:2.11.0-4
- drop src_vipa (#1781683)
- kernel-install: skip BOOT_IMAGE param when copying the cmdline to BLS snippets

* Mon Dec 02 2019 Dan Horák <dan[at]danny.cz> - 2:2.11.0-3
- apply kernel install/update script fixes from #1755899, #1778243

* Mon Dec 02 2019 Dan Horák <dan[at]danny.cz> - 2:2.11.0-2
- apply kernel install/update script fixes from #1600480, #1665060
- merge stage3 signing support from RHEL

* Mon Sep 09 2019 Dan Horák <dan[at]danny.cz> - 2:2.11.0-1
- rebased to 2.11.0

* Mon Aug 05 2019 Dan Horák <dan[at]danny.cz> - 2:2.10.0-1
- rebased to 2.10.0

* Fri Jul 26 2019 Fedora Release Engineering <releng@fedoraproject.org> - 2:2.9.0-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_31_Mass_Rebuild

* Tue Jul 02 2019 Dan Horák <dan[at]danny.cz> - 2:2.9.0-3
- fix /tmp being deleted when kernel-core is installed in a container (#1726286) (javierm)

* Tue Jun 11 17:21:59 CEST 2019 Igor Gnatenko <ignatenkobrain@fedoraproject.org> - 2:2.9.0-2
- Rebuild for RPM 4.15

* Wed May 22 2019 Dan Horák <dan[at]danny.cz> - 2:2.9.0-1
- rebased to 2.9.0

* Thu May 02 2019 Dan Horák <dan[at]danny.cz> - 2:2.8.0-3
- dbginfo.sh needs tar (#1705628)

* Sat Mar 09 2019 Dan Horák <dan[at]danny.cz> - 2:2.8.0-2
- fix building zipl with gcc9 (#1687085)

* Mon Feb 18 2019 Dan Horák <dan[at]danny.cz> - 2:2.8.0-1
- rebased to 2.8.0

* Sat Feb 02 2019 Fedora Release Engineering <releng@fedoraproject.org> - 2:2.7.1-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_30_Mass_Rebuild

* Mon Jan 28 2019 Dan Horák <dan[at]danny.cz> - 2:2.7.1-3
- create cpacfstats group needed by cpacfstatsd

* Thu Jan 10 2019 Dan Horák <dan[at]danny.cz> - 2:2.7.1-2
- load protected key support kernel module early on boot

* Wed Jan 02 2019 Dan Horák <dan[at]danny.cz> - 2:2.7.1-1
- rebased to 2.7.1

* Wed Dec 05 2018 Dan Horák <dan[at]danny.cz> - 2:2.7.0-4
- fix deps for dropped cmsfs subpackage

* Mon Nov 19 2018 Dan Horák <dan[at]danny.cz> - 2:2.7.0-3
- drop the original cmsfs subpackage

* Tue Nov 06 2018 Javier Martinez Canillas <javierm@redhat.com> - 2:2.7.0-2
- Make zipl to use the BLS title field as the IPL section name

* Wed Oct 31 2018 Dan Horák <dan[at]danny.cz> - 2:2.7.0-1
- rebased to 2.7.0

* Mon Oct 22 2018 Dan Horák <dan[at]danny.cz> - 2:2.6.0-8
- don't relink the zkey tools

* Mon Oct 15 2018 Peter Jones <pjones@redhat.com> - 2.6.0-7
- Make the blscfg sort order match what grub2 and grubby do. (pjones)
- Add a ~debug suffix instead of -debug to sort it correctly. (javierm)

* Mon Oct 01 2018 Dan Horák <dan[at]danny.cz> - 2:2.6.0-6
- Fix kernel-install scripts issues

* Fri Sep 21 2018 Dan Horák <dan[at]danny.cz> - 2:2.6.0-5
- Makefile cleanups

* Mon Sep 17 2018 Dan Horák <dan[at]danny.cz> - 2:2.6.0-4
- drop redundant systemd services installation

* Fri Sep 14 2018 Dan Horák <dan[at]danny.cz> - 2:2.6.0-3
- add FIEMAP support into zipl

* Tue Aug 14 2018 Dan Horák <dan[at]danny.cz> - 2:2.6.0-2
- fix R:/BR: perl

* Fri Aug 10 2018 Dan Horák <dan[at]danny.cz> - 2:2.6.0-1
- rebased to 2.6.0
- include zdev dracut module

* Tue Jul 31 2018 Dan Horák <dan[at]danny.cz> - 2:2.5.0-5
- add missing zkey infrastructure (#1610242)

* Fri Jul 27 2018 Dan Horák <dan[at]danny.cz> - 2:2.5.0-4
- don't override TERM for console

* Thu Jul 26 2018 Dan Horák <dan[at]danny.cz> - 2:2.5.0-3
- network-scripts are required for network device initialization

* Sat Jul 14 2018 Fedora Release Engineering <releng@fedoraproject.org> - 2:2.5.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_29_Mass_Rebuild

* Mon Jun 11 2018 Dan Horák <dan[at]danny.cz> - 2:2.5.0-1
- rebased to 2.5.0

* Thu May 24 2018 Javier Martinez Canillas <javierm@redhat.com> - 2:2.4.0-2
- zipl: Add BootLoaderSpec support
- Add kernel-install scripts to create BLS fragment files

* Wed May 09 2018 Dan Horák <dan[at]danny.cz> - 2:2.4.0-1
- rebased to 2.4.0

* Fri Apr 13 2018 Dan Horák <dan[at]danny.cz> - 2:2.3.0-3
- fix building zipl with PIE (#1566140)

* Mon Mar 12 2018 Dan Horák <dan[at]danny.cz> - 2:2.3.0-2
- fix LDFLAGS injection (#1552661)

* Wed Feb 21 2018 Rafael Santos <rdossant@redhat.com> - 2:2.3.0-1
- rebased to 2.3.0

* Fri Feb 09 2018 Fedora Release Engineering <releng@fedoraproject.org> - 2:2.2.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Mon Jan 22 2018 Dan Horák <dan[at]danny.cz> - 2:2.2.0-2
- fix build with non-standard %%dist

* Thu Dec 07 2017 Dan Horák <dan[at]danny.cz> - 2:2.2.0-1
- rebased to 2.2.0

* Mon Sep 25 2017 Dan Horák <dan[at]danny.cz> - 2:2.1.0-1
- rebased to 2.1.0

* Wed Aug 23 2017 Dan Horák <dan[at]danny.cz> - 2:2.0.0-1
- rebased to first public release on github, functionally same as 1.39.0
- relicensed to MIT

* Wed Aug 23 2017 Dan Horák <dan[at]danny.cz> - 2:1.39.0-1
- rebased to 1.39.0
- completed switch to systemd
- further cleanups and consolidation

* Wed Aug 16 2017 Dan Horák <dan@danny.cz> - 2:1.37.1-4
- rebuild for librpm soname bump in rpm 4.13.90

* Thu Aug 03 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2:1.37.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Thu Jul 27 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2:1.37.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Fri May 19 2017 Dan Horák <dan[at]danny.cz> - 2:1.37.1-1
- rebased to 1.37.1
- removed chmem/lsmem as they are now provided by util-linux >= 2.30 (#1452792)

* Sat Feb 11 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2:1.36.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Thu Dec 01 2016 Dan Horák <dan[at]danny.cz> - 2:1.36.1-1
- rebased to 1.36.1

* Wed Sep 07 2016 Dan Horák <dan[at]danny.cz> - 2:1.36.0-1
- rebased to 1.36.0
- switch cpuplugd to systemd service

* Fri Apr 22 2016 Dan Horák <dan[at]danny.cz> - 2:1.34.0-1
- rebased to 1.34.0

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 2:1.30.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Thu Oct 01 2015 Dan Horák <dan[at]danny.cz> - 2:1.30.0-2
- rebuild for librpm soname bump

* Fri Jul 17 2015 Dan Horák <dan[at]danny.cz> - 2:1.30.0-1
- rebased to 1.30.0

* Tue Jun 23 2015 Dan Horák <dan[at]danny.cz> - 2:1.29.0-1
- rebased to 1.29.0
- dropped daemon hardening patch as hardening is enabled globally
- added hmcdrvfs and cpacfstatsd subpackages
- install systemd units where available

* Fri Jun 19 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2:1.23.0-16
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Tue Apr 07 2015 Dan Horák <dan[at]danny.cz> - 2:1.23.0-15
- remove bashism from zfcpconf.sh

* Wed Jan 28 2015 Dan Horák <dan[at]danny.cz> - 2:1.23.0-14
- refresh from RHEL-7
 - update patches
 - add zdsfs subpackage
 - rebase src_vipa to 2.1.0

* Thu Oct 09 2014 Dan Horák <dan[at]danny.cz> - 2:1.23.0-13
- update device_cio_free script
- udpate Requires for ziomon subpackage

* Wed Jun 11 2014 Dan Horák <dan[at]danny.cz> - 2:1.23.0-12
- update for -Werror=format-security

* Sun Jun 08 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2:1.23.0-11
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Tue Mar 04 2014 Dan Horák <dan[at]danny.cz> - 2:1.23.0-10
- fix zFCP device discovery in anaconda GUI (#1054691)

* Mon Feb 10 2014 Dan Horák <dan[at]danny.cz> - 2:1.23.0-9
- znetconf: Allow for 16-char network interface names (#1062285)
- qetharp: Allow for 16-char network interface names (#1062250)

* Mon Feb 03 2014 Dan Horák <dan[at]danny.cz> - 2:1.23.0-8
- znetconf,lsqeth: Allow for 16-char network interface name (#1060303)

* Wed Jan 29 2014 Dan Horák <dan[at]danny.cz> - 2:1.23.0-7
- zipl: Fix zfcpdump "struct job_ipl_data" initialization (#1058856)

* Wed Jan 15 2014 Dan Horák <dan[at]danny.cz> - 2:1.23.0-6
- zipl: fix segmentation fault in automenu array (#1017541)
- zfcpconf.sh: check current online state before setting zfcp device online (#1042496)

* Tue Nov 19 2013 Dan Horák <dan[at]danny.cz> - 2:1.23.0-5
- dbginfo.sh: enhancements for script execution and man page (#1031144)
- dbginfo.sh: avoid double data collection (#1032068)

* Wed Nov 06 2013 Dan Horák <dan[at]danny.cz> - 2:1.23.0-4
- build daemons hardened (#881250)
- zipl: Use "possible_cpus" kernel parameter (#1016180)

* Wed Aug 21 2013 Dan Horák <dan[at]danny.cz> - 2:1.23.0-3
- dbginfo.sh: Avoiding exclusion list for pipes in sysfs (#996732)
- zipl: Fix zipl "--force" option for DASD multi-volume dump (#997361)

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2:1.23.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Wed Jul 24 2013 Dan Horák <dan[at]danny.cz> - 2:1.23.0-1
- rebased to 1.23 (#804774)

* Wed Jun 05 2013 Dan Horák <dan[at]danny.cz> - 2:1.20.0-5
- update with patches from RHEL-6
- rebase zIPL to 1.21 to fix booting from FBA DASD (#970859)

* Tue May 21 2013 Dan Horák <dan[at]danny.cz> - 2:1.20.0-4
- drop the libzfcphbaapi subpackage as it is moved to its own package (#963670)
- update the zfcp udev rules (#958197)
- fix runtime dependencies for osasnmpd (#965413)

* Wed Mar 27 2013 Dan Horák <dan[at]danny.cz> - 2:1.20.0-3
- disable libzfcphbaapi subpackage, fails to build with recent kernels

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2:1.20.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Wed Dec 19 2012 Dan Horák <dan[at]danny.cz> - 2:1.20.0-1
- updated to 1.20.0 (#804774)

* Thu Nov 22 2012 Dan Horák <dan[at]danny.cz> - 2:1.19.0-4
- clean BuildRequires a bit

* Mon Sep 17 2012 Dan Horák <dan[at]danny.cz> - 2:1.19.0-3
- zipl: Flush disk buffers before installing IPL record (#857814)

* Mon Aug 27 2012 Dan Horák <dan[at]danny.cz> 2:1.19.0-2
- add support for CEX4 devices to chzcrypt/lszcrypt (#847092)

* Mon Aug 27 2012 Dan Horák <dan[at]danny.cz> 2:1.19.0-1
- updated to 1.19.0 (#804774)
- fixed syntax in s390.sh script (#851096)
- spec cleanup

* Tue Aug 21 2012 Dan Horák <dan[at]danny.cz> 2:1.17.0-1
- updated to 1.17.0
- add support for new storage device on System z (#847086)

* Thu Aug 16 2012 Dan Horák <dan[at]danny.cz> 2:1.16.0-11
- fix libzfcphbaapi for recent kernels

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2:1.16.0-10
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Fri May 25 2012 Dan Horák <dan[at]danny.cz> 2:1.16.0-9
- improve DASD parameters handling in normalize_dasd_arg (#824807)

* Wed May 23 2012 Dan Horák <dan[at]danny.cz> 2:1.16.0-8
- add normalize_dasd_arg script (#823078)

* Mon May 14 2012 Dan Horák <dan[at]danny.cz> 2:1.16.0-7
- ethtool is required by lsqeth (#821421)

* Fri May 11 2012 Dan Horák <dan[at]danny.cz> 2:1.16.0-6
- updated the Fedora patch set - no vol_id tool in udev (#819530)

* Fri May  4 2012 Dan Horák <dan[at]danny.cz> 2:1.16.0-5
- zipl.conf must be owned by s390utils-base (#818877)

* Tue Apr 17 2012 Dan Horák <dan[at]danny.cz> 2:1.16.0-4
- install the z90crypt udev rule (moved here from the udev package)

* Tue Apr 10 2012 Dan Horák <dan[at]danny.cz> 2:1.16.0-3
- include fixed ccw_init and updated device_cio_free

* Sat Jan 14 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2:1.16.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Thu Dec 15 2011 Dan Horák <dan[at]danny.cz> 2:1.16.0-1
- rebased to 1.16.0

* Tue Aug 16 2011 Dan Horák <dan[at]danny.cz> 2:1.14.0-1
- rebased to 1.14.0

* Wed Apr 27 2011 Dan Horák <dan[at]danny.cz> 2:1.8.2-32
- updated ccw udev rules
- converted cio_free_device from an upstart job to systemd unit (jstodola)
- mon_statd: switch to using udevadm settle (#688140)
- cpuplugd: Fix incorrect multiplication in rules evaluation (#693365)
- cmsfs-fuse: Delete old file if renaming to an existing file (#690505)
- cmsfs-fuse: Enlarge fsname string (#690506)
- cmsfs-fuse: Unable to use cmsfs-fuse if $HOME is not set (#690514)
- hyptop: Prevent interactive mode on s390 line mode terminals (#690810)

* Fri Mar 18 2011 Dan Horák <dhorak@redhat.com> 2:1.8.2-31
- mon_statd: switch to using udevadm settle (#688140)
- hyptop: Fix man page typo for "current weight" (#684244)
- fdasd: buffer overflow when writing to read-only device (#688340)
- cmsfs-fuse: fix read and write errors in text mode (#680465)
- cmsfs-fuse needs fuse (#631546)
- dumpconf: Add DELAY_MINUTES description to man page (#676706)
- iucvterm scriptlet need shadow-utils (#677247)
- use lower-case in udev rules (#597360)
- add support for the 1731/02 OSM/OSX network device (#636849)
- xcec-bridge: fix multicast forwarding (#619504)
- ziomon: wrong return codes (#623250)
- qethconf: process devices with non-zero subchannel (#627692)
- wait for completion of any pending actions affecting device (#631527)
- add infrastructure code for new features (#631541)
- hyptop: Show hypervisor performance data on System z (#631541)
- cmsfs-fuse: support for CMS EDF filesystems via fuse (#631546)
- lsmem/chmem: Tools to manage memory hotplug (#631561)
- dumpconf: Prevent re-IPL loop for dump on panic (#633411)
- ttyrun: run a program if a terminal device is available (#633420)
- zgetdump/zipl: Add ELF dump support (needed for makedumpfile) (#633437)
- znetconf: support for OSA CHPID types OSX and OSM (#633534)
- iucvtty: do not specify z/VM user ID as argument to login -h (#636204)
- tunedasd: add new option -Q / --query_reserve (#644935)
- fdasd/dasdfmt: fix format 7 label (#649787)
- cpuplugd: cmm_pages not set and restored correctly (#658517)
- lsluns: Fix LUN reporting for SAN volume controller (SVC) (#659828)
- lsluns: Accept uppercase and lowercase hex digits (#660361)
- cmsfs: use detected filesystem block size (#651012)
- device_cio_free: use the /proc/cio_settle interface when waiting for devices
- libzfcphbaapi library needs kernel-devel during build and thus is limited to s390x
- libzfcphbaapi library rebased to 2.1 (#633414)
- new zfcp tools added (#633409)

* Wed Feb 09 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2:1.8.2-30
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Tue Jul 13 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-29
- lsluns: uninitialized value on adapter offline (#611795)
- zfcpdbf: Fix 'Use of uninitialized value' and output issues (#612622)

* Wed Jul  7 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-28
- fix linking with --no-add-needed

* Tue Jun 29 2010 Dan Horák <dhorak@redhat.com> 2:1.8.2-27
- make znet_cio_free work also when no interface config files exists (#609073)
- fix --dates option in zfcpdbf (#609092)

* Mon Jun 28 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-26
- follow symlinks in ziorep (#598574)
- do not restrict group names to be alphanumeric in ts-shell (#598641)
- znetconf --drive|-d option returning 'unknown driver' for qeth (#601846)
- fix stack overwrite in cpuplugd (#601847)
- fix cmm_min/max limit checks in cpuplugd (#606366)
- set cpu_min to 1 by default in cpuplugd (#606416)
- build with -fno-strict-aliasing (#599396)
- remove reference to z/VM from the cpi initscript (#601753)
- fix return values for the mon_statd initscript (#606805)
- ignore backup and similar config files in device_cio_free (#533494)

* Fri May 28 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-25
- fixed device_cio_free command line handling (#595569)

* Thu May 20 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-24
- added a check for the length of the parameters line (#594031)

* Wed May 19 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-23
- make ccw_init compatible with posix shell (#546615)

* Wed May  5 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-22
- scripts can't depend on stuff from /usr (#587364)

* Mon May  3 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-21
- updated patch for the "reinitialize array in lsqeth" issue (#587757)

* Fri Apr 30 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-20
- updated lsdasd man page (#587044)
- reinitialize array in lsqeth (#587599)

* Wed Apr 28 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-19
- fixed mismatch between man and -h in chshut (#563625)
- use the merged ccw_init script (#533494, #561814)

* Thu Apr 22 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-18
- lsluns utility from the base subpackage requires sg3_utils

* Wed Apr 21 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-17
- updated device_cio_free script (#576015)

* Wed Mar 31 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-16
- updated device_cio_free upstart config file (#578260)
- fix multipathing in ziomon (#577318)

* Mon Mar 29 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-15
- remove check for ziorep_config availability (#576579)
- install upstart event file into /etc/init (#561339)
- device_cio_free updates
    - don't use basename/dirname
    - correctly parse /etc/ccw.conf (#533494)

* Mon Mar 22 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-14
- don't use memory cgroups in zfcpdump kernel (#575183)
- fix df usage in ziomon (#575833)

* Thu Mar 11 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-13
- dropped dependency on redhat-lsb (#542702)

* Wed Mar 10 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-12
- run device_cio_free on startup (#561339)
- use hex index for chpidtype table in znetconf (#561056)
- handle status during IPL SSCH (#559250)
- don't show garbage in vmconvert's progress bar (#567681)
- don't print enviroment when there are no devices to wait for (#570763)
- fix zfcp dump partition error (#572313)
- switched to new initscripts for cpuplugd and fsstatd/procd (#524218, #524477)

* Tue Feb 16 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-11
- moved ccw udev stuff from initscripts to s390utils
- updated ccw_init with delay loops and layer2 handling (#561926)

* Fri Jan 22 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-10.1
- really update zfcpconf.sh script from dracut

* Wed Jan 20 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-10
- fixed return codes in ziorep (#556849)
- fixed return code in lstape (#556910)
- fixed reading the size of /proc/sys/vm/cmm_pages in cpuplugd (#556911)
- support new attributes in lsqeth (#556915)

* Wed Jan 13 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-9
- updated device_cio_free script (#533494)
- fixed uppercase conversion in lscss (#554768)

* Fri Jan  8 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-8
- updated device_cio_free script (#533494)

* Fri Jan  8 2010 Dan Horák <dan[at]danny.cz> 2:1.8.2-7
- updated device_cio_free script (#533494)

* Tue Dec 22 2009 Dan Horák <dan[at]danny.cz> 2:1.8.2-6.1
- fixed return value in cpi initscript (#541389)

* Tue Dec 22 2009 Dan Horák <dan[at]danny.cz> 2:1.8.2-6
- fixed return value in cpi initscript (#541389)
- updated zfcpconf.sh script from dracut
- added device-mapper support into zipl (#546280)
- added missing check and print NSS name in case an NSS has been IPLed (#546297)
- added device_cio_free script and its symlinks (#533494)
- added qualified return codes and further error handling in znetconf (#548487)

* Fri Nov 13 2009 Dan Horák <dan[at]danny.cz> 2:1.8.2-5
- added multiple fixes from IBM (#533955, #537142, #537144)

* Thu Nov 12 2009 Dan Horák <dan[at]danny.cz> 2:1.8.2-4
- added udev rules and script for dasd initialization (#536966)
- added ghosted zfcp and dasd config files, fixes their ownership on the system
- fixed upgrade path for libzfcphbaapi-devel subpackage

* Mon Nov  9 2009 Dan Horák <dan[at]danny.cz> 2:1.8.2-3
- added files for the CPI feature (#463282)
- built lib-zfcp-hbaabi library as vendor lib, switched from -devel (no devel content now) to -docs subpackage (#532707)

* Fri Oct 30 2009 Dan Horák <dan[at]danny.cz> 2:1.8.2-2
- install dasd udev rules provided by the s390-tools
- added patch for setting readahead value

* Thu Oct  8 2009 Dan Horák <dan[at]danny.cz> 2:1.8.2-1
- added patch for improving mon_statd behaviour
- rebased to 1.8.2

* Fri Oct  2 2009 Dan Horák <dan[at]danny.cz> 2:1.8.1-8
- really changed ramdisk load address (#526339)
- change the required and optional subpackages for the meta package

* Wed Sep 30 2009 Dan Horák <dan[at]danny.cz> 2:1.8.1-7
- changed ramdisk load address (#526339)
- updated zfcpconf.sh script to new sysfs interface (#526324)
- added 1.8.1 fixes from IBM (#525495)

* Fri Sep 25 2009 Dan Horák <dan[at]danny.cz> 2:1.8.1-6
- fix issues in lib-zfcp-hbaapi with a patch

* Thu Sep 24 2009 Dan Horák <dan[at]danny.cz> 2:1.8.1-5
- drop support for Fedora < 10

* Thu Sep 24 2009 Dan Horák <dan[at]danny.cz> 2:1.8.1-4
- fixed string overflow in vtoc_volume_label_init (#525318)

* Thu Sep  3 2009 Dan Horák <dan[at]danny.cz> 2:1.8.1-3
- create devel subpackage with some useful headers
- preserving timestamps on installed files

* Wed Aug 26 2009 Dan Horák <dan[at]danny.cz> 2:1.8.1-2
- Fix byte check for disk encryption check in lsluns (#510032)
- Fix cmm configuration file value initialization parser in cpuplugd (#511379)
- Check only ZFCP devices in lszfcp (#518669)

* Mon Jun 29 2009 Dan Horák <dan[at]danny.cz> 2:1.8.1-1
- update to 1.8.1
- drop upstreamed patches
- create iucvterm subpackage
- update src_vipa locations patch
- install cmsfs tools into /sbin
- add post 1.8.1 fixes from IBM

* Fri Apr 17 2009 Dan Horák <dan[at]danny.cz> 2:1.8.0-6
- fix build with newer kernels

* Wed Mar 25 2009 Dan Horák <dan[at]danny.cz> 2:1.8.0-5
- reword the summaries a bit
- add downloadable URLs for Sources
- fix CFLAGS usage

* Fri Mar 13 2009 Dan Horák <dan[at]danny.cz> 2:1.8.0-4
- next round of clean-up for compliance with Fedora

* Sun Mar  8 2009 Dan Horák <dan[at]danny.cz> 2:1.8.0-3
- little clean-up for compliance with Fedora

* Fri Dec 12 2008 Hans-Joachim Picht <hans@linux.vnet.ibm.com> 2:1.8.0-2
- Adapted package for F9

* Tue Dec 9 2008 Michael Holzheu <michael.holzheu@de.ibm.com> 2:1.8.0-1
- Changed spec file to create sub packages
- Updated to zfcphbaapi version 2.0

* Tue Oct 28 2008 Dan Horák <dan[at]danny.cz> 2:1.7.0-4
- disable build-id feature in zipl (#468017)

* Wed Sep 24 2008 Dan Horák <dan[at]danny.cz> 2:1.7.0-3
- drop the mon_tools patch (mon_statd service starts both mon_procd and mon_fsstatd since 1.7.0)

* Thu Aug 28 2008 Dan Horák <dan[at]danny.cz> 2:1.7.0-2
- preserve timestamps on installed files
- add proper handling of initscripts
- fix permissions for some files

* Tue Aug 12 2008 Dan Horák <dan[at]danny.cz> 2:1.7.0-1
- update to s390-tools 1.7.0, src_vipa 2.0.4 and cmsfs 1.1.8c
- rebase or drop RHEL5 patches

* Fri Jul 25 2008 Dan Horák <dhorak@redhat.com> 2:1.5.3-19.el5
- fix use "vmconvert" directly on the vmur device node (#439389)
- fix the Linux Raid partition type is not retained when changed through fdasd (#445271)
- include missing files into the package (#442584)
- Resolves: #439389, #445271, #442584

* Fri Jul 25 2008 Dan Horák <dhorak@redhat.com> 2:1.5.3-18.el5
- split the warnings patch into s390-tools and cmsfs parts
- mismatch between installed /etc/zfcp.conf and zfcpconf.sh expected format (#236016)
- dbginfo.sh exits before running all tests and drops errors (#243299)
- updates for cleanup SCSI dumper code for upstream integration - tool (#253118)
- fix segfault when using LD_PRELOAD=/usr/lib64/src_vipa.so (#282751)
- add support for timeout parameter in /etc/zipl.conf (#323651)
- fixes not listing all the dasds passed as arguments to lsdasd command (#369891)
- fix for zipl fail when section is specified and target is not repeated for all sections (#381201)
- fix for dasdview -s option fails to ignore the garbage value passed (#412951)
- update documentation for zfcpdump (#437477)
- update documentation for lsqeth (#455908)
- Resolves: #236016, #243299, #253118, #282751, #323651, #369891, #381201, #412951, #437477, #455908

* Fri Mar 28 2008 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-17.el5
- Fix error messages and proc/0 entry are not handled correctly (#438819)

* Wed Feb 06 2008 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-16.el5
- Fixed a build problem with the mon_tools patch (#253029)

* Mon Feb 04 2008 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-14.el5
- Added zfcpdump kernel symlink to dumpconf init script (#430550)

* Fri Jan 18 2008 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-13.el5
- Fix tape390_crypt query shows wrong msg 'Kernel does not support tape encryption' (#269181)

* Wed Jan 16 2008 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-12.el5
- Add System z guest file system size in Monitor APPLDATA (#253029)
- Add Dynamic CHPID reconfiguration via SCLP - tools (#253076)
- Add z/VM unit-record device driver - tools (#253078)
- Cleanup SCSI dumper code for upstream integration - tool (#253118)

* Tue Jan 08 2008 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-11.el5
- Fix installer LVM partitions that show up as "unknown" in fdasd (#250176)
- Fixed zfcpconf.sh failure if / and /usr are separated (#279201)

* Mon Sep 24 2007 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-10.el5.14
- Added missing openssl-devel buildrequires (#281361)

* Thu Aug 23 2007 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-10.el5.13
- Last updage for -t parameter patch (#202086)

* Tue Aug 14 2007 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-10.el5.12
- Fix handling of external timer interrupts (#250352)

* Tue Jul 31 2007 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-10.el5.11
- Update fix for -t parameter for image operations (#202086)

* Fri Jul 27 2007 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-10.el5.10
- Fixed udev regression from RHEL 4 with /dev/dasd/ (#208189)
- Fixed missing -d option for zgetdump (#228094)

* Thu Jun 28 2007 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-10.el5.9
- Fix optional -t parameter for image operations (#202086)

* Wed Jun 27 2007 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-10.el5.8
- Fix wrong manpage (#202250)
- Fix zfcp devices not showing up after boot (#223569)
- Fix help menu of lsqeth showing wrong file (#225159)
- Add tape encryption userspace tool (#228080)
- Add dump on panic initscript and sysconf (#228094)
- Fix a off-by-one error in zfcpdbf (#230527)
- Fix zipl aborting with floating point exception if the target specified is a logical volume (#231240)
- Fix boot menu use wrong conversion table for input on LPAR (#240399)

* Mon Jan 22 2007 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-10.el5.6
- Fixed problem with invisible zfcp devices after boot (#223569)

* Mon Jan 15 2007 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-10.el5.5
- Extended fix for automenu bug (#202086)

* Thu Jan 11 2007 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-10.el5.4
- Updated dbginfo.sh patch to final fix from IBM (#214805)

* Wed Nov 29 2006 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-10.el5.3
- Fixed problem with missing debugfs for dbginfo.sh (#214805)

* Thu Nov 09 2006 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-10.el5.2
- Fixed lszfcp bug related to sysfsutils (#210515)

* Tue Nov 07 2006 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-10.el5.1
- Removed wrong additional $ in src_vipa.sh (#213395)
- Release and Buildroot specfile fixes

* Wed Sep 13 2006 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-10
- Needed to bump release

* Tue Sep 12 2006 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-9
- Added libsysfs requirement (#201863)
- Fixed zipl problem with missing default target for automenus (#202086)

* Thu Aug 10 2006 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-8
- Added missing sysfsutils requirement for lszfcp (#201863)

* Tue Jul 25 2006 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-7
- Included zfcpdbf, dbginfo.sh and the man1 manpages to package (#184812)

* Tue Jul 18 2006 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-6
- Disabled sysfs support due to API changes in sysfs-2.0.0

* Fri Jul 14 2006 Karsten Hopp <karsten@redhat.de> 2:1.5.3-5
- buildrequire net-snmp-devel

* Fri Jul 14 2006 Jesse Keating <jkeating@redhat.com> - 2:1.5.3-4
- rebuild
- Add missing br libsysfs-devel, indent, zlib-devel

* Wed May 17 2006 Phil Knirsch <pknirsch@redhat.com> 2:1.5.3-1
- Made src_vipa build on current toolchain again

* Tue May 16 2006 Phil Knirsch <pknirsch@redhat.com>
- Update to s390-tools-1.5.3 from IBM
- Included vmconvert
- Dropped obsolete asm patch

* Tue Feb 07 2006 Jesse Keating <jkeating@redhat.com> - 2:1.5.0-2.1
- rebuilt for new gcc4.1 snapshot and glibc changes

* Mon Jan 30 2006 Phil Knirsch <pknirsch@redhat.com> 2:1.5.0-2
- Fixed problem with s390-tools-1.5.0-fdasd-raid.patch
- Don't try to remove the non empty _bindir
- Some more install cleanups

* Thu Jan 26 2006 Phil Knirsch <pknirsch@redhat.com>
- Fixed some .macro errors in zipl/boot

* Fri Dec 09 2005 Jesse Keating <jkeating@redhat.com>
- rebuilt

* Thu Oct 20 2005 Phil Knirsch <pknirsch@redhat.com> 2:1.5.0-1
- Large update from 1.3.2 to 1.5.0
- Include osasnmpd and vmcp now by default

* Tue Sep 06 2005 Phil Knirsch <pknirsch@redhat.com> 2:1.3.2-7
- Fixed a couple of code bugs (#143808)

* Fri Jul 29 2005 Phil Knirsch <pknirsch@redhat.com> 2:1.3.2-6
- Corrected filelist for libdir to only include *.so files

* Tue Jun 21 2005 Phil Knirsch <pknirsch@redhat.com> 2:1.3.2-5
- Added src_vipa to s390utils

* Wed Mar 02 2005 Phil Knirsch <pknirsch@redhat.com> 2:1.3.2-4
- bump release and rebuild with gcc 4

* Tue Oct 26 2004 Phil Knirsch <pknirsch@redhat.com> 2:1.3.2-3
- Put binaries for system recovery in /sbin again.

* Fri Oct 15 2004 Phil Knirsch <pknirsch@redhat.com> 2:1.3.2-1
- Update to s390-tools-1.3.2
- Added qetharp, qethconf, ip_watcher, tunedasd and various other tools to
  improve functionality on s390(x).

* Wed Oct 06 2004 Phil Knirsch <pknirsch@redhat.com> 2:1.3.1-7
- Made the raid patch less verbose (#129656)

* Thu Sep 16 2004 Phil Knirsch <pknirsch@redhat.com> 2:1.3.1-6
- Added prompt=1 and timeout=15 to automatically generated menu

* Tue Aug 31 2004 Karsten Hopp <karsten@redhat.de> 2:1.3.1-5
- install zfcpconf.sh into /sbin

* Tue Aug 24 2004 Karsten Hopp <karsten@redhat.de> 2:1.3.1-4 
- add zfcpconf.sh to read /etc/zfcp.conf and configure the zfcp
  devices

* Thu Jun 24 2004 Phil Knirsch <pknirsch@redhat.com> 2:1.3.1-3
- Fixed another automenu bug with dumpto and dumptofs (#113204).

* Thu Jun 17 2004 Phil Knirsch <pknirsch@redhat.com> 2:1.3.1-2
- Fixed automenu patch.
- Fixed problem with installation from tape (#121788).

* Wed Jun 16 2004 Phil Knirsch <pknirsch@redhat.com> 2:1.3.1-1
- Updated to latest upstream version s390-tools-1.3.1

* Tue Jun 15 2004 Elliot Lee <sopwith@redhat.com>
- rebuilt

* Mon Jun 07 2004 Karsten Hopp <karsten@redhat.com>
- add cmsfs utils

* Tue Mar 02 2004 Elliot Lee <sopwith@redhat.com>
- rebuilt

* Thu Feb 19 2004 Phil Knirsch <pknirsch@redhat.com> 2:1.2.4-4
- Fixed rebuilt on fc2.

* Thu Feb 19 2004 Phil Knirsch <pknirsch@redhat.com> 2:1.2.4-3
- Fixed automenu patch, was allocating 1 line to little.

* Mon Feb 16 2004 Phil Knirsch <pknirsch@redhat.com> 2:1.2.4-2
- rebuilt

* Mon Feb 16 2004 Phil Knirsch <pknirsch@redhat.com> 2:1.2.4-1
- Updated to latest developerworks release 1.2.4
- Disabled zfcpdump build until i find a way to build it as none-root.

* Fri Feb 13 2004 Elliot Lee <sopwith@redhat.com> 2:1.2.3-3
- rebuilt

* Thu Dec 04 2003 Phil Knirsch <pknirsch@redhat.com> 2:1.2.3-2
- Fixed zfcpdump build.

* Fri Nov 28 2003 Phil Knirsch <pknirsch@redhat.com> 2:1.2.3-1
- New bugfix release 1.2.3 came out today, updated again.

* Wed Nov 26 2003 Phil Knirsch <pknirsch@redhat.com> 2:1.2.2-1
- Updated to latest Developerworks version 1.2.2
- Cleaned up specfile and patches a little.

* Wed Nov 12 2003 Phil Knirsch <pknirsch@redhat.com> 2:1.2.1-4.1
- rebuilt

* Wed Nov 12 2003 Phil Knirsch <pknirsch@redhat.com> 2:1.2.1-4
- Another fix for the new automenu patch. Target was an optional parameter in
  old s390utils, provided compatibility behaviour.

* Mon Oct 20 2003 Phil Knirsch <pknirsch@redhat.com> 2:1.2.1-3.1
- rebuilt

* Mon Oct 20 2003 Phil Knirsch <pknirsch@redhat.com> 2:1.2.1-3
- Small fix for the new automenu patch, default section didn't work correctly

* Mon Oct 20 2003 Phil Knirsch <pknirsch@redhat.com> 2:1.2.1-2.1
- rebuilt

* Fri Oct 17 2003 Phil Knirsch <pknirsch@redhat.com> 2:1.2.1-2
- Patched new zipl to be backwards compatible to old multiboot feature.

* Thu Oct  9 2003 Harald Hoyer <harald@redhat.de> 2:1.2.1-1
- second round at updating to 1.2.1

* Thu Oct 09 2003 Florian La Roche <Florian.LaRoche@redhat.de>
- first round at updating to 1.2.1

* Sat Sep 27 2003 Florian La Roche <Florian.LaRoche@redhat.de>
- add /boot/tape0 for .tdf tape boots

* Fri Jul 25 2003 Florian La Roche <Florian.LaRoche@redhat.de>
- apply dasdfmt patch from 1.2.1

* Fri Jun 20 2003 Phil Knirsch <pknirsch@redhat.com> 1.1.7-1
- Updated to latest upstream version 1.1.7

* Fri May 02 2003 Pete Zaitcev <zaitcev@redhat.com> 1.1.6-7
- Fix usage of initialized permissions for bootmap.

* Tue Apr 29 2003 Florian La Roche <Florian.LaRoche@redhat.de>
- add extra tape loader from Pete Zaitcev

* Mon Apr 14 2003 Karsten Hopp <karsten@redhat.de> 2:1.1.6-5
- drop cpint support

* Mon Mar 24 2003 Karsten Hopp <karsten@redhat.de> 1.1.6-4
- use multiboot as default
- add option to disable multiboot 

* Sat Mar 22 2003 Karsten Hopp <karsten@redhat.de> 1.1.6-3
- add multiboot patch

* Mon Mar 10 2003 Karsten Hopp <karsten@redhat.de> 1.1.6-2
- added percentage patch (used by anaconda to display progress bars)

* Thu Feb 27 2003 Phil Knirsch <pknirsch@redhat.com> 1.1.6-1
- Updated to newest upstream version 1.1.6

* Tue Feb 04 2003 Phil Knirsch <pknirsch@redhat.com> 1.1.5-1
- Updated to newest upstream version 1.1.5

* Tue Feb 04 2003 Karsten Hopp <karsten@redhat.de> 1.1.4-3
- install libraries in /lib*, not /usr/lib*, they are required
  by some tools in /sbin

* Sun Feb 02 2003 Florian La Roche <Florian.LaRoche@redhat.de>
- fix filelist to not include debug files

* Fri Jan 24 2003 Phil Knirsch <pknirsch@redhat.com> 1.1.4-1
- Updated to latest upstream version of IBM.
- Removed all unecessary patches and updated still needed patches.
- Fixed version number. Needed to introduce epoch though.
- A little specfile cleanup.
- Dropped oco-setver and oco-convert as we don't need them anymore.

* Wed Jan 22 2003 Phil Knirsch <pknirsch@redhat.com> 20020226-4
- Added ExclusiveArch tag.

* Mon Oct 21 2002 Phil Knirsch <pknirsch@redhat.com> 20020226-3
- Removed fdisk -> fdasd symlink. Is now provided by util-linux.
- Disabled f5 patch for s390x for now. Enable it later for newer kernels again.

* Mon May 27 2002 Phil Knirsch <pknirsch@redhat.com>
- Fixed dasdview to build on kernels > 2.4.18.

* Wed Apr 24 2002 Karsten Hopp <karsten@redhat.de>
- add IBM 5 patch

* Tue Jan 29 2002 Karsten Hopp <karsten@redhat.de>
- add IBM 4 patch
- add profile.d scripts to set correct TERM in 3270 console

* Tue Dec 18 2001 Karsten Hopp <karsten@redhat.de>
- add cpint programs

* Mon Nov 26 2001 Harald Hoyer <harald@redhat.de> 20011012-6
- fix for #56720

* Thu Nov 15 2001 Karsten Hopp <karsten@redhat.de>
- add fdisk - > fdasd symlink

* Mon Nov 12 2001 Karsten Hopp <karsten@redhat.de>
- add IBM patch (11/09/2001) and redo percentage patch

* Thu Nov 08 2001 Karsten Hopp <karsten@redhat.de>
- re-enable DASD if dasdfmt is interrupted with Ctrl-C

* Mon Nov 05 2001 Harald Hoyer <harald@redhat.de> 20011012-4
- added s390-tools-dasdfmt-percentage.patch

* Mon Oct 22 2001 Karsten Hopp <karsten@redhat.de>
- remove postinstall script

* Mon Oct 15 2001 Karsten Hopp <karsten@redhat.de>
- add IBM's s390-utils-2.patch
- add console to securetty

* Mon Oct 01 2001 Karsten Hopp <karsten@redhat.de>
- added oco-setkver and oco-convert

* Fri Aug 31 2001 Karsten Hopp <karsten@redhat.de>
- don't write error message in silent mode

* Thu Aug 23 2001 Harald Hoyer <harald@redhat.de>
- added s390-tools-dasdfmt-status.patch

* Tue Aug 21 2001 Karsten Hopp <karsten@redhat.de>
- update to the version from Aug 20

* Tue Aug 14 2001 Karsten Hopp <karsten@redhat.de>
- fix permissions

* Mon Aug 13 2001 Karsten Hopp <karsten@redhat.de>
- rename package to s390utils. s390-tools is no longer needed.

* Thu Aug 02 2001 Karsten Hopp <karsten@redhat.de>
- initial build
